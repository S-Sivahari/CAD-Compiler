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
        open_freecad (optional): "true" to open in FreeCAD after generation.

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

    open_freecad = request.form.get("open_freecad", "false").lower() == "true"

    # --- Save uploaded file ---
    try:
        step_path = _save_upload(file)
    except Exception as e:
        logger.error(f"Upload save failed: {e}")
        return jsonify({"error": True, "message": f"Failed to save upload: {str(e)}"}), 500

    # --- Run edit pipeline ---
    logger.info(f"Running edit pipeline: prompt='{prompt}', file={step_path}")
    result = edit_pipeline.edit_step(step_path, prompt, open_freecad=open_freecad)

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
