import os
import re
import sys
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Set

import cadquery as cq
from OCP.BRepAlgoAPI import BRepAlgoAPI_Defeaturing
from OCP.TopTools import TopTools_ListOfShape
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.gp import gp_Vec

from step_editor import step_analyzer
from core import config
from utils.logger import setup_logger

logger = setup_logger('synthocad.step_editor', 'step_editor.log')

# ---------------------------------------------------------------------------
# Isolated boolean helper
# ---------------------------------------------------------------------------
_RESIZE_WORKER = """
import sys, json, cadquery as cq
p = json.loads(sys.argv[1])
model = cq.importers.importStep(p['step_in'])
plane = cq.Plane(origin=cq.Vector(*p['loc']), normal=cq.Vector(*p['axis']))
old_r  = p['old_radius']
new_r  = p['new_radius']
tool_h = p['tool_h']
tol    = p['tol']
if p['is_hole']:
    fill   = cq.Workplane(plane).circle(old_r + tol).extrude(tool_h, both=True)
    filled = model.union(fill)
    cut    = cq.Workplane(plane).circle(new_r).extrude(tool_h, both=True)
    result = filled.cut(cut)
else:
    if new_r < old_r:
        outer  = cq.Workplane(plane).circle(old_r + tol).extrude(tool_h, both=True)
        inner  = cq.Workplane(plane).circle(new_r).extrude(tool_h, both=True)
        sleeve = outer.cut(inner)
        result = model.cut(sleeve)
    else:
        tool   = cq.Workplane(plane).circle(new_r).extrude(tool_h, both=True)
        result = model.union(tool)
cq.exporters.export(result, p['step_out'])
"""

_REPOSITION_WORKER = """
import sys, json, cadquery as cq
p = json.loads(sys.argv[1])
model = cq.importers.importStep(p['step_in'])
old_plane = cq.Plane(origin=cq.Vector(*p['old_loc']), normal=cq.Vector(*p['axis']))
new_plane = cq.Plane(origin=cq.Vector(*p['new_loc']), normal=cq.Vector(*p['axis']))
radius = p['radius']
tool_h = p['tool_h']
tol    = p['tol']
if p['is_hole']:
    fill   = cq.Workplane(old_plane).circle(radius + tol).extrude(tool_h, both=True)
    model  = model.union(fill)
    cut    = cq.Workplane(new_plane).circle(radius).extrude(tool_h, both=True)
    result = model.cut(cut)
else:
    outer  = cq.Workplane(old_plane).circle(radius + tol).extrude(tool_h, both=True)
    model  = model.cut(outer)
    boss   = cq.Workplane(new_plane).circle(radius).extrude(tool_h)
    result = model.union(boss)
cq.exporters.export(result, p['step_out'])
"""

_CREATE_WORKER = """
import sys, json, cadquery as cq
p = json.loads(sys.argv[1])
model   = cq.importers.importStep(p['step_in'])
loc     = p['loc']
axis    = p['axis']
radius  = p['radius']
height  = p['height']
is_hole = p['is_hole']
ftype   = p.get('feat_type', 'cylinder')
top_r   = p.get('top_radius', 0.0)
plane   = cq.Plane(origin=cq.Vector(*loc), normal=cq.Vector(*axis))
if ftype == 'cone':
    tip = max(top_r, 0.001)
    tool = cq.Workplane(plane).circle(radius).workplane(offset=height).circle(tip).loft()
else:
    tool = cq.Workplane(plane).circle(radius).extrude(height)
if is_hole:
    result = model.cut(tool)
else:
    result = model.union(tool)
cq.exporters.export(result, p['step_out'])
"""


def _isolated_cyl_resize(
    current_model: "cq.Workplane",
    loc: list, axis: list,
    old_radius: float, new_radius: float,
    is_hole: bool, tool_h: float,
    timeout: int = 120,
) -> "cq.Workplane":
    """
    Run the full cylinder resize inside an isolated subprocess so that a
    C-level OCC abort() cannot kill the Flask process.
    Returns the resized model on success; raises ValueError on crash/timeout.
    """
    tmp_in  = tempfile.NamedTemporaryFile(suffix='.step', delete=False)
    tmp_out = tempfile.NamedTemporaryFile(suffix='.step', delete=False)
    tmp_in.close()
    tmp_out.close()
    try:
        logger.info("[Execute] Exporting model to temp STEP for isolated boolean...")
        cq.exporters.export(current_model, tmp_in.name)

        params = json.dumps({
            'step_in':    tmp_in.name,
            'step_out':   tmp_out.name,
            'loc':        loc,
            'axis':       axis,
            'old_radius': old_radius,
            'new_radius': new_radius,
            'is_hole':    is_hole,
            'tool_h':     tool_h,
            'tol':        0.05,
        })

        logger.info(
            f"[Execute] Spawning isolated boolean subprocess "
            f"(is_hole={is_hole}, new_r={new_radius}, timeout={timeout}s)..."
        )
        try:
            proc = subprocess.run(
                [sys.executable, '-c', _RESIZE_WORKER, params],
                timeout=timeout,
                capture_output=True,
                text=True,
            )
        except subprocess.TimeoutExpired:
            raise ValueError(
                f"Boolean operation timed out after {timeout}s. "
                "Model is likely too complex for this operation."
            )

        if proc.returncode != 0:
            stderr = proc.stderr.strip() or "(no stderr)"
            logger.error(
                f"[Execute] Isolated boolean subprocess failed "
                f"(exit {proc.returncode}): {stderr}"
            )
            raise ValueError(
                f"Boolean operation crashed (exit {proc.returncode}). "
                f"OCC likely aborted on the complex solid. Details: {stderr}"
            )

        if not os.path.exists(tmp_out.name) or os.path.getsize(tmp_out.name) == 0:
            raise ValueError(
                "Boolean subprocess reported success but output STEP is missing/empty."
            )

        logger.info("[Execute] Isolated boolean succeeded. Loading result...")
        result = cq.importers.importStep(tmp_out.name)
        logger.info("[Execute] Result loaded successfully.")
        return result
    finally:
        for path in (tmp_in.name, tmp_out.name):
            try:
                os.unlink(path)
            except OSError:
                pass


def _run_isolated_worker(worker_script: str, params: dict, label: str, timeout: int = 120) -> "cq.Workplane":
    """
    Generic helper: exports current_model (keyed as 'step_in') to a temp file,
    runs worker_script in a child process, reads back 'step_out'.
    params must already include 'step_in' and 'step_out' keys pointing to
    the temp files (created by the caller).
    """
    params_json = json.dumps(params)
    logger.info(f"[Execute] Spawning isolated subprocess: {label} (timeout={timeout}s)")
    try:
        proc = subprocess.run(
            [sys.executable, '-c', worker_script, params_json],
            timeout=timeout,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired:
        raise ValueError(f"{label} timed out after {timeout}s. Model may be too complex.")

    if proc.returncode != 0:
        stderr = proc.stderr.strip() or "(no stderr)"
        logger.error(f"[Execute] {label} subprocess failed (exit {proc.returncode}): {stderr}")
        raise ValueError(f"{label} crashed (exit {proc.returncode}). Details: {stderr}")

    if not os.path.exists(params['step_out']) or os.path.getsize(params['step_out']) == 0:
        raise ValueError(f"{label} subprocess succeeded but output STEP is missing/empty.")

    logger.info(f"[Execute] {label} succeeded. Loading result...")
    return cq.importers.importStep(params['step_out'])


def _isolated_reposition(
    current_model: "cq.Workplane",
    old_loc: list, new_loc: list, axis: list,
    radius: float, height: float,
    is_hole: bool, timeout: int = 120,
) -> "cq.Workplane":
    """Move an existing hole/boss from old_loc to new_loc in an isolated subprocess."""
    tool_h = max(height * 3.0, 50.0)
    tmp_in  = tempfile.NamedTemporaryFile(suffix='.step', delete=False)
    tmp_out = tempfile.NamedTemporaryFile(suffix='.step', delete=False)
    tmp_in.close(); tmp_out.close()
    try:
        cq.exporters.export(current_model, tmp_in.name)
        params = {
            'step_in': tmp_in.name, 'step_out': tmp_out.name,
            'old_loc': old_loc, 'new_loc': new_loc, 'axis': axis,
            'radius': radius, 'tool_h': tool_h, 'tol': 0.05, 'is_hole': is_hole,
        }
        return _run_isolated_worker(_REPOSITION_WORKER, params, 'Reposition', timeout)
    finally:
        for p in (tmp_in.name, tmp_out.name):
            try: os.unlink(p)
            except OSError: pass


def _isolated_create(
    current_model: "cq.Workplane",
    loc: list, axis: list,
    radius: float, height: float,
    is_hole: bool,
    feat_type: str = 'cylinder',
    top_radius: float = 0.0,
    timeout: int = 120,
) -> "cq.Workplane":
    """Create a new cylinder or cone feature (hole or boss) in an isolated subprocess."""
    tmp_in  = tempfile.NamedTemporaryFile(suffix='.step', delete=False)
    tmp_out = tempfile.NamedTemporaryFile(suffix='.step', delete=False)
    tmp_in.close(); tmp_out.close()
    try:
        cq.exporters.export(current_model, tmp_in.name)
        params = {
            'step_in': tmp_in.name, 'step_out': tmp_out.name,
            'loc': loc, 'axis': axis, 'radius': radius, 'height': height,
            'is_hole': is_hole, 'feat_type': feat_type, 'top_radius': top_radius,
        }
        return _run_isolated_worker(_CREATE_WORKER, params, f'Create {feat_type}', timeout)
    finally:
        for p in (tmp_in.name, tmp_out.name):
            try: os.unlink(p)
            except OSError: pass


def _get_action_from_llm(prompt: str, features: dict, provider: str = 'gemini') -> list:
    sys.path.append(str(Path(__file__).parent.parent))

    if provider == 'ollama':
        from services.ollama_service import call_ollama as _call_llm
        _kwargs = {'model': 'qwen2.5:7b', 'temperature': 0.0}
        _provider_label = 'Qwen (Ollama)'
    else:
        from services.gemini_service import call_gemini as _call_llm
        _kwargs = {}
        _provider_label = 'Gemini'

    context_str = json.dumps(features, indent=2)
    context_bytes = len(context_str.encode())
    logger.info(f"[LLM] Sending context: {context_bytes} bytes, "
                f"{len(features.get('cylinders', []))} cyls, "
                f"{len(features.get('planes', []))} planes")

    system_prompt = f"""You must output ONLY the raw JSON array. No explanation, no markdown, no prose.
    You are a CAD editing assistant mapping user text directly to a geometric operation.
    Given this dictionary of existing geometric features in the model:
    {context_str}
    
    And the user's edit prompt:
    "{prompt}"
    
    Return a strictly formatted JSON array of action objects. Support multiple faces if asked!
    Supported actions:
    
    1. Resize a Hole (internal cylinder, e.g. bore/through-hole):
    {{"action": "resize_hole", "face_id": "f5", "new_radius": 3.0}}
    
    2. Resize an external Shaft / Boss / Cylinder:
    {{"action": "resize_hole", "face_id": "f10", "new_radius": 1.0}}
    (Use the same action for both — the system detects hole vs shaft automatically.)
    
    3. Defeature (Delete a feature entirely):
    {{"action": "defeature", "face_id": "f12"}}
    
    4. Extrude / Move a Planar Face (to change block dimensions, etc.):
    {{"action": "extrude_face", "face_id": "f4", "distance": 5.0}}
    (Positive distance pushes outward adding volume. Negative distance pushes inward cutting volume.)
    
    5. Reposition a Hole or Cylinder / Cone to a new XYZ location (keeps all other geometry):
    {{"action": "reposition", "face_id": "f5", "new_location": [x, y, z]}}
    The axis direction is preserved; only the centre position moves.
    
    6. Create a brand-new Cylinder or cylindrical Hole at any position:
    {{"action": "create_cylinder", "location": [x, y, z], "axis": [0, 0, 1], "radius": 5.0, "height": 20.0, "is_hole": false}}
    Set "is_hole": true to cut a hole, false to add a solid boss/cylinder.
    
    7. Create a brand-new Cone or conical Hole at any position:
    {{"action": "create_cone", "location": [x, y, z], "axis": [0, 0, 1], "base_radius": 10.0, "top_radius": 0.0, "height": 15.0, "is_hole": false}}
    "top_radius": 0.0 = sharp tip; >0 = frustum (truncated cone). Set "is_hole": true to cut.
    
    If the user mentions multiple faces / operations, return a list of JSON objects!
    Output exactly the raw JSON array (or object). Do not output markdown, no conversational text.
    """
    
    try:
        logger.info(f"[LLM] Calling {_provider_label}...")
        response_text = _call_llm(system_prompt, **_kwargs)
        logger.info(f"[LLM] Raw response ({len(response_text)} chars): {response_text!r}")
        
        json_str = response_text
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0]
            logger.debug("[LLM] Stripped ```json fences")
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0]
            logger.debug("[LLM] Stripped ``` fences")
            
        json_str = json_str.strip()
        logger.debug(f"[LLM] JSON string to parse: {json_str!r}")
        
        try:
            parsed = json.loads(json_str)
            result = parsed if isinstance(parsed, list) else [parsed]
            logger.info(f"[LLM] Parsed actions: {result}")
            return result
        except json.JSONDecodeError as je:
            logger.warning(f"[LLM] Direct JSON parse failed ({je}), trying fallback search")
            # Fallback search for list or dict
            start = response_text.find('[')
            end = response_text.rfind(']')
            if start != -1 and end != -1:
                extracted = response_text[start:end+1]
                logger.info(f"[LLM] Fallback array extract: {extracted!r}")
                result = json.loads(extracted)
                logger.info(f"[LLM] Fallback parsed actions: {result}")
                return result
            start = response_text.find('{')
            end = response_text.rfind('}')
            if start != -1 and end != -1:
                extracted = response_text[start:end+1]
                logger.info(f"[LLM] Fallback object extract: {extracted!r}")
                result = [json.loads(extracted)]
                logger.info(f"[LLM] Fallback parsed actions: {result}")
                return result
            raise ValueError("No JSON array/object found in LLM response.")
            
    except Exception as e:
        logger.error(f"[LLM] Failed to get action from LLM: {e}", exc_info=True)
        raise ValueError(f"Failed to interpret edit prompt using LLM: {e}")


# Fallback limits when no explicit face IDs are found in the prompt.
_MAX_LLM_CYLINDERS = 80
_MAX_LLM_PLANES    = 30


def _face_ids_in_prompt(prompt: str) -> Set[str]:
    """Return the set of face IDs (e.g. 'f49', 'f0') explicitly named in the prompt."""
    return {m.lower() for m in re.findall(r'\bf\d+\b', prompt, re.IGNORECASE)}


def execute_edit_from_prompt(step_path: str, prompt: str, pre_analyzed_features: dict = None, provider: str = 'gemini') -> Dict[str, Any]:
    logger.info(f"[Pipeline] execute_edit_from_prompt: prompt={prompt!r}, step={step_path}")

    if pre_analyzed_features:
        logger.info("[Pipeline] Using pre-analyzed features (skipping re-analysis)")
        features = pre_analyzed_features
    else:
        logger.info("[Pipeline] No pre-analyzed features -- running step_analyzer.analyze()")
        features = step_analyzer.analyze(step_path)

    all_cyls   = features.get("cylinders", [])
    all_planes = features.get("planes", [])
    face_count = features.get("face_count", 0)
    logger.info(
        f"[Pipeline] Features: {face_count} total faces, "
        f"{len(all_cyls)} cylinders, {len(all_planes)} planes"
    )

    named_ids = _face_ids_in_prompt(prompt)
    logger.info(f"[Pipeline] Face IDs in prompt: {named_ids or '(none - natural language)'}")

    if named_ids:
        cyls_ctx   = [c for c in all_cyls   if c["id"] in named_ids]
        planes_ctx = [p for p in all_planes if p["id"] in named_ids]
        logger.info(
            f"[Pipeline] Named-ID mode: found {len(cyls_ctx)} cyl(s) and "
            f"{len(planes_ctx)} plane(s) matching {named_ids}"
        )
        if not cyls_ctx and not planes_ctx:
            logger.warning(
                f"[Pipeline] WARNING: face ID(s) {named_ids} were not found in "
                f"cylinders or planes.  The face may be a cone/torus/other type. "
                f"Available cylinder IDs: {[c['id'] for c in all_cyls[:20]]} ..."
            )
        simplified_features = {
            "bounding_box": features.get("bounding_box", {}),
            "cylinders":    cyls_ctx,
            "planes":       planes_ctx,
            "summary":      features.get("summary", ""),
            "_note":        f"Showing only the {len(named_ids)} face(s) named in the prompt out of {face_count} total.",
        }
    else:
        truncated = len(all_cyls) > _MAX_LLM_CYLINDERS or len(all_planes) > _MAX_LLM_PLANES
        simplified_features = {
            "bounding_box": features.get("bounding_box", {}),
            "cylinders":    all_cyls[:_MAX_LLM_CYLINDERS],
            "planes":       all_planes[:_MAX_LLM_PLANES],
            "summary":      features.get("summary", ""),
        }
        if truncated:
            simplified_features["_note"] = (
                f"Model has {face_count} total faces. "
                f"Showing first {_MAX_LLM_CYLINDERS} cylinders and "
                f"{_MAX_LLM_PLANES} planes only."
            )
        logger.info(
            f"[Pipeline] Natural-language mode: sending "
            f"{len(simplified_features['cylinders'])} cyls / "
            f"{len(simplified_features['planes'])} planes to LLM"
        )

    commands = _get_action_from_llm(prompt, simplified_features, provider=provider)
    logger.info(f"[Pipeline] LLM determined actions: {commands}")

    return execute_action(step_path, commands, features)


def execute_action(step_path: str, commands: List[dict], original_features: dict) -> Dict[str, Any]:
    logger.info(f"[Execute] Loading STEP for edit: {step_path}")
    try:
        model = cq.importers.importStep(step_path)
    except Exception as e:
        logger.error(f"[Execute] STEP import failed: {e}", exc_info=True)
        raise ValueError(f"Failed to load STEP for editing: {e}")

    # We must fetch the original faces before modifying the topology!
    faces = model.faces().vals()
    logger.info(f"[Execute] STEP loaded. Total faces in model: {len(faces)}")

    # Handle both single-Solid and Compound (multi-body assembly) STEP files.
    raw_shape = model.val().wrapped
    try:
        current_model = cq.Workplane(cq.Solid(raw_shape))
        logger.info("[Execute] Model wrapped as single Solid")
    except Exception as e:
        logger.warning(f"[Execute] cq.Solid() failed ({e}) - treating as Compound/assembly")
        current_model = model

    # Actions that reference an existing face by ID
    _FACE_TARGETED = {"resize_hole", "defeature", "extrude_face", "reposition"}

    for cmd_idx, command in enumerate(commands):
        action = command.get("action")
        face_id = command.get("face_id", "")
        logger.info(f"[Execute] Command {cmd_idx+1}/{len(commands)}: action={action!r}, face_id={face_id!r}, params={command}")

        target_face = None
        idx = -1
        if action in _FACE_TARGETED:
            if not face_id:
                raise ValueError(f"Action '{action}' requires a face_id.")
            try:
                idx = int(face_id.replace("f", ""))
            except ValueError:
                raise ValueError(f"Invalid face_id format: {face_id!r}")
            if idx < 0 or idx >= len(faces):
                raise ValueError(
                    f"Face ID {idx} out of bounds (model has {len(faces)} faces, "
                    f"valid range: f0-f{len(faces)-1})."
                )
            logger.info(f"[Execute] face_id={face_id!r} -> index {idx} of {len(faces)}")
            target_face = faces[idx]
        
        # Handle Extrude directly (no defeaturing needed)
        if action == "extrude_face":
            distance = float(command.get("distance", 0))
            if distance == 0:
                continue
                
            try:
                cq_face = cq.Face(target_face.wrapped)
                norm = cq_face.normalAt()
                vec = gp_Vec(norm.x * distance, norm.y * distance, norm.z * distance)
                
                prism_api = BRepPrimAPI_MakePrism(cq_face.wrapped, vec)
                if not prism_api.IsDone():
                    raise ValueError("Failed to construct prism from face.")
                    
                extruded_solid = cq.Solid(prism_api.Shape())
                wp_tool = cq.Workplane(extruded_solid)
                
                if distance > 0:
                    current_model = current_model.union(wp_tool)
                else:
                    current_model = current_model.cut(wp_tool)
                    
            except Exception as e:
                logger.error(f"Face extrude failed: {e}")
                raise ValueError(f"Failed to extrude face {face_id}. Overlapping topology issues?")
                
        elif action == "resize_hole":
            new_radius = float(command.get("new_radius", 0))
            if new_radius <= 0:
                raise ValueError("Invalid new_radius for resize_hole.")

            all_cyl_ids = [c["id"] for c in original_features.get("cylinders", [])]
            logger.info(
                f"[Execute] resize_hole: looking for {face_id!r} among "
                f"{len(all_cyl_ids)} cylinders. First 10 IDs: {all_cyl_ids[:10]}"
            )

            cyl_data = next(
                (c for c in original_features.get("cylinders", []) if c["id"] == face_id),
                None,
            )
            if not cyl_data:
                logger.error(
                    f"[Execute] face {face_id!r} NOT found in cylinder list. "
                    f"All cylinder IDs: {all_cyl_ids}"
                )
                raise ValueError(
                    f"Could not find face {face_id} in cylinder features. "
                    f"Available cylinder IDs: {all_cyl_ids}"
                )

            logger.info(
                f"[Execute] cyl_data for {face_id}: radius={cyl_data['radius_mm']}, "
                f"is_hole={cyl_data.get('is_hole')}, height={cyl_data.get('height_mm')}, "
                f"loc={cyl_data['location']}, axis={cyl_data['axis']}"
            )

            loc        = cyl_data["location"]
            axis       = cyl_data["axis"]
            old_radius = float(cyl_data["radius_mm"])
            is_hole    = bool(cyl_data.get("is_hole", True))
            height     = float(cyl_data.get("height_mm", 200))

            # Generous extrusion height - spans the full cylinder regardless of
            # where loc sits relative to the face centre.
            tool_h = max(height * 3.0, 50.0)

            logger.info(
                f"[Execute] Dispatching to isolated subprocess: "
                f"is_hole={is_hole}, old_r={old_radius}, new_r={new_radius}, "
                f"tool_h={tool_h:.2f}, loc={loc}, axis={axis}"
            )
            current_model = _isolated_cyl_resize(
                current_model,
                loc=loc, axis=axis,
                old_radius=old_radius, new_radius=new_radius,
                is_hole=is_hole, tool_h=tool_h,
            )
            logger.info(f"[Execute] resize_hole completed for {face_id}")

        elif action == "reposition":
            new_loc = command.get("new_location")
            if not new_loc or len(new_loc) != 3:
                raise ValueError("reposition requires 'new_location': [x, y, z]")

            cyl_data = next(
                (c for c in original_features.get("cylinders", []) if c["id"] == face_id),
                None,
            )
            if not cyl_data:
                raise ValueError(
                    f"Could not find face {face_id} in cylinder features for reposition. "
                    f"Available IDs: {[c['id'] for c in original_features.get('cylinders', [])]}"
                )

            old_loc    = cyl_data["location"]
            axis       = cyl_data["axis"]
            radius     = float(cyl_data["radius_mm"])
            height     = float(cyl_data.get("height_mm", 50))
            is_hole    = bool(cyl_data.get("is_hole", True))

            logger.info(
                f"[Execute] Repositioning {face_id}: {old_loc} -> {new_loc}, "
                f"r={radius}, is_hole={is_hole}"
            )
            current_model = _isolated_reposition(
                current_model,
                old_loc=old_loc, new_loc=new_loc, axis=axis,
                radius=radius, height=height, is_hole=is_hole,
            )
            logger.info(f"[Execute] Reposition completed for {face_id}")

        elif action == "create_cylinder":
            loc     = command.get("location", [0.0, 0.0, 0.0])
            axis    = command.get("axis", [0.0, 0.0, 1.0])
            radius  = float(command.get("radius", 5.0))
            height  = float(command.get("height", 10.0))
            is_hole = bool(command.get("is_hole", False))

            if radius <= 0 or height <= 0:
                raise ValueError("create_cylinder: radius and height must be > 0")

            logger.info(
                f"[Execute] Creating cylinder: r={radius}, h={height}, "
                f"loc={loc}, axis={axis}, is_hole={is_hole}"
            )
            current_model = _isolated_create(
                current_model,
                loc=loc, axis=axis, radius=radius, height=height,
                is_hole=is_hole, feat_type='cylinder',
            )
            logger.info("[Execute] create_cylinder completed")

        elif action == "create_cone":
            loc        = command.get("location", [0.0, 0.0, 0.0])
            axis       = command.get("axis", [0.0, 0.0, 1.0])
            base_r     = float(command.get("base_radius", 5.0))
            top_r      = float(command.get("top_radius", 0.0))
            height     = float(command.get("height", 10.0))
            is_hole    = bool(command.get("is_hole", False))

            if base_r <= 0 or height <= 0:
                raise ValueError("create_cone: base_radius and height must be > 0")

            logger.info(
                f"[Execute] Creating cone: base_r={base_r}, top_r={top_r}, h={height}, "
                f"loc={loc}, axis={axis}, is_hole={is_hole}"
            )
            current_model = _isolated_create(
                current_model,
                loc=loc, axis=axis, radius=base_r, height=height,
                is_hole=is_hole, feat_type='cone', top_radius=top_r,
            )
            logger.info("[Execute] create_cone completed")

        elif action == "defeature":
            # Pure remove — still uses BRepAlgoAPI_Defeaturing but only when
            # the user explicitly requests a complete feature removal.
            face_count_total = len(faces)
            if face_count_total > 300:
                raise ValueError(
                    f"Pure defeature is not supported on models with "
                    f"{face_count_total} faces (limit 300) -- the OCC "
                    "defeaturing kernel is unreliable at that complexity."
                )
            try:
                shape_to_remove = target_face.wrapped
                remove_list = TopTools_ListOfShape()
                remove_list.Append(shape_to_remove)
                solid = current_model.val().wrapped
                api = BRepAlgoAPI_Defeaturing()
                api.SetShape(solid)
                api.AddFacesToRemove(remove_list)
                api.SetRunParallel(True)
                api.Build()
                if not api.IsDone():
                    raise ValueError(
                        "OpenCASCADE Defeaturing API failed. "
                        "Geometry may be too complex."
                    )
                healed_solid = api.Shape()
            except Exception as e:
                logger.error(f"Defeaturing failed on face {face_id}: {e}")
                raise ValueError(
                    f"Could not remove face {face_id}. "
                    "It may be modified, intersecting, or the solid is too complex."
                )
            try:
                current_model = cq.Workplane(cq.Solid(healed_solid))
            except Exception:
                current_model = cq.Workplane().newObject(
                    [cq.Shape.cast(healed_solid)]
                )

        else:
            raise ValueError(f"Unsupported action: {action}")
    
    import uuid
    out_filename = f"edited_{uuid.uuid4().hex[:8]}.step"
    out_path = config.STEP_OUTPUT_DIR / out_filename
    config.STEP_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"[Execute] All commands done. Exporting to {out_path}")
    try:
        cq.exporters.export(current_model, str(out_path))
    except Exception as e:
        logger.error(f"[Execute] STEP export failed: {e}", exc_info=True)
        raise ValueError(f"Failed to export edited STEP file: {e}")
    logger.info(f"[Execute] Export complete: {out_path}")
    
    return {
        "status": "success",
        "step_file": str(out_path)
    }

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python step_executor.py <file.step> <prompt>")
        sys.exit(1)
    res = execute_edit_from_prompt(sys.argv[1], sys.argv[2])
    print(res)
