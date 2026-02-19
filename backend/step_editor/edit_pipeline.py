"""Edit Pipeline - Orchestrates the full STEP editing workflow.

Flow:
    STEP file
        → step_analyzer  (exact geometry: cylinders, planes, bbox)
        → call_gemini / call_ollama  (new SCL JSON synthesis)
        → SynthoCadPipeline.process_from_json  (generate new STEP)
"""
import os
import sys
import json
import uuid
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, Optional

sys.path.append(str(Path(__file__).parent.parent))

from step_editor import step_analyzer
from services.gemini_service import call_gemini
from services.ollama_service import call_ollama
from core.main import SynthoCadPipeline
from core import config

logger = logging.getLogger(__name__)

# ─── LLM Prompt Template ──────────────────────────────────────────────────────

EDIT_SYSTEM_PROMPT = """You are an expert parametric CAD engineer converting existing STEP geometry into editable SCL (SynthoCAD Language) JSON.

CRITICAL OUTPUT RULES:
1. Output ONLY valid raw JSON — no markdown, no explanation, no comments.
2. The JSON MUST have a "parts" key with at least "part_1".
3. "part_1" MUST use "NewBodyFeatureOperation".
4. Each part needs EXACTLY ONE of: sketch+extrusion, revolve_profile+revolve, or hole_feature.
5. Sketch coordinates are normalized (0.0-1.0), then sketch_scale converts to real mm.
6. Always include "units": "mm".

REQUIRED JSON SKELETON (fill in values, preserve structure):
{
  "final_name": "Edited_Part",
  "final_shape": "Box",
  "units": "mm",
  "parts": {
    "part_1": {
      "coordinate_system": {
        "Euler Angles": [0.0, 0.0, 0.0],
        "Translation Vector": [0.0, 0.0, 0.0]
      },
      "sketch": {
        "face_1": {
          "loop_1": {
            "line_1": {"Start Point": [0.0, 0.0], "End Point": [1.0, 0.0]},
            "line_2": {"Start Point": [1.0, 0.0], "End Point": [1.0, 1.0]},
            "line_3": {"Start Point": [1.0, 1.0], "End Point": [0.0, 1.0]},
            "line_4": {"Start Point": [0.0, 1.0], "End Point": [0.0, 0.0]}
          }
        }
      },
      "extrusion": {
        "extrude_depth_towards_normal": 0.2,
        "extrude_depth_opposite_normal": 0.0,
        "sketch_scale": 5.0,
        "operation": "NewBodyFeatureOperation"
      },
      "description": {
        "name": "Base Body",
        "shape": "Box",
        "length": 5.0,
        "width": 5.0,
        "height": 1.0
      }
    }
  }
}

SCALING RULES:
- BOX: sketch is unit square [0,0]->[1,0]->[1,1]->[0,1]. sketch_scale = width_mm.
- extrude_depth_towards_normal IS ABSOLUTE MM if using sketch_scale=1.0,
  OR relative if sketch_scale > 1.0.
  RECOMMENDED: Set sketch_scale to width, then extrude_depth = height/width.
- Example: 10x10x2mm box -> sketch_scale=10.0, extrude_depth=0.2.
"""

def _build_edit_prompt(features: Dict, user_prompt: str) -> str:
    """Build the full LLM prompt combining geometric features and user intent."""
    parts = [EDIT_SYSTEM_PROMPT]

    parts.append("\n\n=== GEOMETRIC FEATURE REPORT (EXACT) ===")
    parts.append(f"Summary: {features.get('summary', 'N/A')}")
    parts.append(f"Bounding Box: {json.dumps(features.get('bounding_box', {}))}")

    if features.get("cylinders"):
        parts.append(f"\nCylindrical Features ({len(features['cylinders'])} total):")
        for c in features["cylinders"]:
            parts.append(
                f"  - ID {c['id']}: radius={c['radius_mm']}mm, "
                f"axis={c['axis']}, location={c['location']}"
            )

    if features.get("planes"):
        z_faces = [p for p in features["planes"] if abs(p["normal"][2]) > 0.9]
        if z_faces:
            parts.append(f"\nMain Flat Faces (normal ≈ Z-axis):")
            for p in z_faces:
                parts.append(f"  - ID {p['id']}: dims={p['dims']}mm at z={p['location'][2]}mm")

    if features.get("cones"):
        parts.append(f"\nConical Features ({len(features['cones'])} total - likely countersinks):")
        for c in features["cones"]:
            parts.append(f"  - ID {c['id']}: half_angle={c['half_angle_deg']}°")

    parts.append(f"\n\n=== USER EDIT REQUEST ===\n{user_prompt}")
    parts.append("\n\nGenerate the SCL JSON output:")

    return "\n".join(parts)


# ─── Main Entry Point ──────────────────────────────────────────────────────────

def edit_step(step_path: str, user_prompt: str, open_freecad: bool = False) -> Dict[str, Any]:
    """
    Run the full STEP editing pipeline.

    Args:
        step_path:    Path to the uploaded STEP file.
        user_prompt:  Natural language description of the desired change.
        open_freecad: Whether to open the result in FreeCAD.

    Returns:
        Result dict from SynthoCadPipeline (status, step_file, py_file, etc.)
        with an extra key "features" containing the analysis report.
    """
    logger.info(f"[EditPipeline] Starting edit: '{user_prompt}' on {step_path}")

    # 1. Geometric Decompilation
    logger.info("[EditPipeline] Step 1: Analyzing geometry...")
    try:
        features = step_analyzer.analyze(step_path)
    except Exception as e:
        return {"status": "error", "error": {"code": "ANALYSIS_FAILED", "message": str(e)}}

    # 2. LLM Synthesis
    logger.info(f"[EditPipeline] Step 2: Synthesizing new SCL JSON via {config.LLM_PROVIDER}...")
    full_prompt = _build_edit_prompt(features, user_prompt)

    try:
        if config.LLM_PROVIDER == "ollama":
            raw_response = call_ollama(full_prompt, max_tokens=4096, temperature=0.1)
        else:
            raw_response = call_gemini(full_prompt, max_tokens=8192, temperature=0.15)
    except Exception as e:
        return {"status": "error", "error": {"code": "LLM_FAILED", "message": f"{config.LLM_PROVIDER} failed: {str(e)}"}}

    # 3. Parse JSON from LLM response
    import re
    raw_response = raw_response.strip()
    if raw_response.startswith("```"):
        raw_response = "\n".join(raw_response.split("\n")[1:])
        raw_response = raw_response.split("```")[0].strip()
    match = re.search(r"\{[\s\S]*\}", raw_response)
    if match:
        raw_response = match.group()

    try:
        scl_json = json.loads(raw_response)
    except json.JSONDecodeError as e:
        return {
            "status": "error",
            "error": {"code": "JSON_PARSE_FAILED", "message": str(e), "raw": raw_response[:500]},
        }

    # 4. Generate the new STEP via existing pipeline
    logger.info("[EditPipeline] Step 3: Generating new STEP file...")
    pipeline = SynthoCadPipeline()
    result = pipeline.process_from_json(scl_json, open_freecad=open_freecad)

    # 5. Attach analysis features to result
    result["features"] = features

    logger.info(f"[EditPipeline] Done. Status: {result.get('status')}")
    return result
