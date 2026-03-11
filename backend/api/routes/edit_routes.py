"""Edit Routes - API endpoints for STEP file editing.

Blueprint: /api/v1/edit

Endpoints:
    POST /api/v1/edit/from-step   Upload a STEP + prompt, get a new STEP back.
    POST /api/v1/edit/analyze     Upload a STEP, return only the feature analysis.
    POST /api/v1/edit/preview     Upload a STEP, return 7-angle labeled images.
"""
import os
import uuid
import logging
from pathlib import Path
from flask import Blueprint, request, jsonify

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from core import config
from step_editor import edit_pipeline, step_analyzer, step_renderer
from utils.logger import api_logger

bp = Blueprint("edit", __name__)
logger = api_logger


def _save_upload(file_storage) -> str:
    """Save an uploaded file to the uploads directory and return its path."""
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}_{file_storage.filename}"
    save_path = config.UPLOAD_DIR / safe_name
    file_storage.save(str(save_path))
    logger.info(f"Saved upload: {save_path}")
    return str(save_path)


@bp.route("/from-step", methods=["POST"])
def edit_from_step():
    """
    Upload a STEP file + edit prompt, receive a new edited STEP file.

    Form Data:
        file   (required): The .step file to edit.
        prompt (required): Natural language edit instruction.

    Returns:
        JSON with status, step_url, features analysis, and visual description.
    """
    # --- Validate inputs ---
    if "file" not in request.files:
        return jsonify({"error": True, "message": "No file uploaded. Use form key 'file'."}), 400

    file = request.files["file"]
    if not file.filename or not file.filename.lower().endswith(".step"):
        return jsonify({"error": True, "message": "Uploaded file must be a .step file."}), 400

    prompt = request.form.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": True, "message": "Edit prompt is required."}), 400

    # --- Save uploaded file ---
    try:
        step_path = _save_upload(file)
    except Exception as e:
        logger.error(f"Upload save failed: {e}")
        return jsonify({"error": True, "message": f"Failed to save upload: {str(e)}"}), 500

    # --- Run edit pipeline ---
    provider = request.form.get('provider', 'gemini')
    logger.info(f"Running edit pipeline: prompt='{prompt}', provider={provider}, file={step_path}")
    result = edit_pipeline.edit_step(step_path, prompt, provider=provider)

    # --- Cleanup upload ---
    try:
        os.remove(step_path)
    except Exception:
        pass

    if result.get("status") == "error":
        return jsonify({"error": True, **result["error"]}), 500

    # --- Build response ---
    step_file = result.get("step_file", "")
    step_url = ""
    if step_file:
        step_filename = Path(step_file).name
        step_url = f"/outputs/step/{step_filename}"

    return jsonify({
        "status": "success",
        "step_url": step_url,
        "step_file": step_file,
        "py_file": result.get("py_file"),
        "json_file": result.get("json_file"),
        "parameters": result.get("parameters", {}),
        "features": result.get("features", {}),
    }), 200


@bp.route("/brep", methods=["POST"])
def edit_brep():
    """
    Upload a STEP file + semantic edit prompt, receive a new edited STEP file.
    Uses direct B-Rep face defeaturing and rebuilding.
    """
    if "file" not in request.files:
        return jsonify({"error": True, "message": "No file uploaded."}), 400

    file = request.files["file"]
    if not file.filename or not file.filename.lower().endswith(".step"):
        return jsonify({"error": True, "message": "Uploaded file must be a .step file."}), 400

    prompt = request.form.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": True, "message": "Edit prompt is required."}), 400

    try:
        step_path = _save_upload(file)
    except Exception as e:
        logger.error(f"Upload save failed: {e}")
        return jsonify({"error": True, "message": f"Failed to save upload: {str(e)}"}), 500

    # Execute B-Rep semantic editing
    from step_editor import step_executor
    provider = request.form.get('provider', 'gemini')
    try:
        result = step_executor.execute_edit_from_prompt(step_path, prompt, provider=provider)
    except Exception as e:
        logger.error(f"B-Rep execution failed: {e}")
        try: os.remove(step_path)
        except: pass
        return jsonify({"error": True, "message": str(e)}), 500

    # Cleanup input
    try: os.remove(step_path)
    except: pass

    if result.get("status") == "error":
        return jsonify({"error": True, "message": result.get("message", "Unknown error")}), 500

    step_file = result.get("step_file", "")
    step_url = ""
    if step_file:
        step_filename = Path(step_file).name
        step_url = f"/outputs/step/{step_filename}"

    return jsonify({
        "status": "success",
        "step_url": step_url,
        "step_file": step_file,
    }), 200


@bp.route("/analyze", methods=["POST"])
def analyze_step():
    """
    Upload a STEP file and return only the geometric feature analysis.
    Useful for inspecting what features were detected before editing.

    Form Data:
        file (required): The .step file to analyze.

    Returns:
        JSON with cylinders, planes, cones, bounding_box, summary.
    """
    if "file" not in request.files:
        return jsonify({"error": True, "message": "No file uploaded."}), 400

    file = request.files["file"]
    if not file.filename or not file.filename.lower().endswith(".step"):
        return jsonify({"error": True, "message": "Uploaded file must be a .step file."}), 400

    try:
        step_path = _save_upload(file)
        features = step_analyzer.analyze(step_path)
        os.remove(step_path)
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return jsonify({"error": True, "message": str(e)}), 500

    return jsonify({"status": "success", "features": features}), 200


@bp.route("/preview", methods=["POST"])
def preview_step():
    """
    Upload a STEP file and receive 7 labeled feature-map images (one per view angle)
    plus the full feature JSON.

    The 7 views are: isometric, top, bottom, front, back, left, right.
    Each view only draws edges visible from that direction.
    Images are saved in outputs/previews/<stem>/ and served via HTTP.

    Form Data:
        file (required): The .step file to preview.

    Returns:
        JSON with:
          - features:    full analysis dict (cylinders, planes, bounding_box, summary)
          - image_urls:  list of {view, label, url} dicts — one per angle (7 total)
          - instructions: Human-readable guide on how to use the feature IDs
    """
    if "file" not in request.files:
        return jsonify({"error": True, "message": "No file uploaded."}), 400

    file = request.files["file"]
    if not file.filename or not file.filename.lower().endswith(".step"):
        return jsonify({"error": True, "message": "Uploaded file must be a .step file."}), 400

    try:
        step_path = _save_upload(file)
        step_stem = Path(step_path).stem

        # 1. Analyze geometry
        features = step_analyzer.analyze(step_path)

        # 2. Render 7-view multi-angle labeled images
        view_paths = step_renderer.render_multiview(step_path, features, str(config.PREVIEWS_DIR))

        # Cleanup uploaded STEP (images are kept in PREVIEWS_DIR for serving)
        os.remove(step_path)

    except Exception as e:
        logger.error(f"Preview failed: {e}")
        return jsonify({"error": True, "message": str(e)}), 500

    # Build view URL list
    VIEW_LABELS = {
        "isometric": "Isometric",
        "top":       "Top",
        "bottom":    "Bottom",
        "front":     "Front",
        "back":      "Back",
        "left":      "Left",
        "right":     "Right",
    }
    image_urls = []
    for view_name, img_path in view_paths.items():
        filename = Path(img_path).name
        image_urls.append({
            "view":  view_name,
            "label": VIEW_LABELS.get(view_name, view_name.capitalize()),
            "url":   f"/outputs/previews/{step_stem}/{filename}",
        })

    instructions = _build_instructions(features)

    return jsonify({
        "status":       "success",
        "features":     features,
        "image_urls":   image_urls,
        "instructions": instructions,
    }), 200


@bp.route("/preview-by-name", methods=["POST"])
def preview_step_by_name():
    """
    Generate preview images for a STEP file already on disk (e.g. after generation).

    JSON Body:
        { "filename": "Cylinder.step" }

    Returns the same payload as /preview (features, image_urls, instructions).
    """
    data = request.get_json(silent=True) or {}
    filename = data.get("filename", "")

    if not filename or not filename.lower().endswith(".step"):
        return jsonify({"error": True, "message": "filename is required and must end with .step"}), 400

    step_path = config.STEP_OUTPUT_DIR / filename
    if not step_path.exists():
        return jsonify({"error": True, "message": f"STEP file not found: {filename}"}), 404

    try:
        step_stem = step_path.stem

        features = step_analyzer.analyze(str(step_path))
        view_paths = step_renderer.render_multiview(str(step_path), features, str(config.PREVIEWS_DIR))

    except Exception as e:
        logger.error(f"Preview-by-name failed: {e}")
        return jsonify({"error": True, "message": str(e)}), 500

    VIEW_LABELS = {
        "isometric": "Isometric", "top": "Top", "bottom": "Bottom",
        "front": "Front", "back": "Back", "left": "Left", "right": "Right",
    }
    image_urls = []
    for view_name, img_path in view_paths.items():
        fname = Path(img_path).name
        image_urls.append({
            "view":  view_name,
            "label": VIEW_LABELS.get(view_name, view_name.capitalize()),
            "url":   f"/outputs/previews/{step_stem}/{fname}",
        })

    instructions = _build_instructions(features)

    return jsonify({
        "status":       "success",
        "features":     features,
        "image_urls":   image_urls,
        "instructions": instructions,
    }), 200


@bp.route("/upload", methods=["POST"])
def upload_step():
    """
    Upload a STEP file to the backend's data/uploads directory for OCP analysis.
    The file is saved with its original filename (with a counter suffix to avoid collisions).

    Form Data:
        file (required): The .step file to upload.

    Returns:
        JSON with url field pointing to the uploaded file.
    """
    if "file" not in request.files:
        return jsonify({"error": True, "message": "No file uploaded."}), 400

    file = request.files["file"]
    if not file.filename or not file.filename.lower().endswith((".step", ".stp")):
        return jsonify({"error": True, "message": "Uploaded file must be a .step or .stp file."}), 400

    upload_dir = Path(__file__).parent.parent.parent.parent / "data" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Use original filename; append counter to avoid overwriting
    original_name = Path(file.filename).name
    save_path = upload_dir / original_name
    counter = 1
    while save_path.exists():
        stem = Path(original_name).stem
        suffix = Path(original_name).suffix
        save_path = upload_dir / f"{stem}_{counter}{suffix}"
        counter += 1

    try:
        file.save(str(save_path))
        logger.info(f"Uploaded STEP file: {save_path}")
    except Exception as e:
        logger.error(f"Upload save failed: {e}")
        return jsonify({"error": True, "message": f"Failed to save upload: {str(e)}"}), 500

    return jsonify({
        "status": "success",
        "filename": save_path.name,
        "url": f"/data/uploads/{save_path.name}",
    }), 200


def _build_instructions(features: dict) -> str:
    """Build a human-readable guide for using feature IDs in the edit prompt."""
    lines = ["Use these feature IDs in your edit prompt:"]

    for c in features.get("cylinders", []):
        lines.append(
            f"  • '{c['id']}' — Cylinder, radius={c['radius_mm']}mm  "
            f"→ e.g. 'change {c['id']} radius to 8mm'"
        )

    for p in features.get("planes", []):
        dims = p.get("dims", [0, 0])
        if dims[0] * dims[1] < 0.01:
            continue
        n = p["normal"]
        face_name = "top face" if n[2] > 0.5 else "bottom face" if n[2] < -0.5 else "side face"
        lines.append(
            f"  • '{p['id']}' — Plane ({face_name}), {dims[0]:.1f}×{dims[1]:.1f}mm"
        )

    bb = features.get("bounding_box", {})
    if bb:
        lines.append(f"\nOverall size: {bb.get('x_mm')}×{bb.get('y_mm')}×{bb.get('z_mm')}mm")

    return "\n".join(lines)
