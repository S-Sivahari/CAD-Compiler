"""Edit Pipeline - Orchestrates the full STEP editing workflow.

Flow (lossless BREP path):
    STEP file
        → step_analyzer  (exact geometry: cylinders, planes, bbox)
        → step_executor._get_action_from_llm  (small LLM call: prompt → action list)
        → step_executor.execute_action  (direct BREP edit on original STEP)

The original STEP geometry is never discarded.  Only the specific face(s)
mentioned in the prompt are modified in-place via OpenCASCADE defeaturing +
re-cut operations.
"""
import os
import re
import sys
import json
import uuid
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, Optional

sys.path.append(str(Path(__file__).parent.parent))

from step_editor import step_analyzer
from step_editor.step_executor import execute_edit_from_prompt
from core import config

logger = logging.getLogger(__name__)


# ─── Main Entry Point ──────────────────────────────────────────────────────────

def edit_step(step_path: str, user_prompt: str, open_freecad: bool = False, provider: str = 'gemini') -> Dict[str, Any]:
    """
    Run the lossless STEP editing pipeline.

    Analyses the STEP geometry, maps the natural-language prompt to a
    concrete BREP action (resize_hole / defeature / extrude_face) via a
    *small* focused LLM call, then applies that action directly to the
    original STEP file using OpenCASCADE.

    The rest of the model is untouched — only the target face(s) change.

    Args:
        step_path:    Path to the uploaded STEP file.
        user_prompt:  Natural language description of the desired change.
        open_freecad: Unused (kept for API compatibility).

    Returns:
        Result dict with keys: status, step_file, features.
    """
    logger.info(f"[EditPipeline] Lossless BREP edit: '{user_prompt}' on {step_path}")

    # 1. Geometric analysis (features used both for the action-LLM and the response)
    logger.info("[EditPipeline] Step 1: Analyzing geometry...")
    try:
        features = step_analyzer.analyze(step_path)
    except Exception as e:
        return {"status": "error", "error": {"code": "ANALYSIS_FAILED", "message": str(e)}}

    # 2. BREP-level edit — original STEP is preserved, only target face changes
    logger.info("[EditPipeline] Step 2: Applying direct BREP edit...")
    try:
        result = execute_edit_from_prompt(
            step_path,
            user_prompt,
            pre_analyzed_features=features,   # skip double-analysis
            provider=provider,
        )
    except Exception as e:
        logger.error(f"[EditPipeline] BREP edit failed: {e}")
        return {"status": "error", "error": {"code": "BREP_EDIT_FAILED", "message": str(e)}}

    # 3. Attach geometry features to result so the frontend can update the panel
    result["features"] = features

    logger.info(f"[EditPipeline] Done. Status: {result.get('status')}")
    return result
