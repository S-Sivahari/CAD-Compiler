import os
import json
import uuid
import tempfile
import subprocess
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple

from core import config
from utils.logger import setup_logger

logger = setup_logger('synthocad.brep_engine', 'brep_engine.log')

# =============================================================================
# ISOLATED WORKERS (Prevent C-level OCC crashes from killing the backend)
# =============================================================================

_BREP_WORKER_SCRIPT = """
import sys, json, math, traceback
import cadquery as cq
from OCP.gp import gp_Pnt, gp_Dir, gp_Ax2
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder

def main():
    try:
        p = json.loads(sys.argv[1])
        op_type = p['type']
        params = p.get('params', {})
        step_in = p.get('step_in')
        step_out = p['step_out']
        
        # Load existing model if provided (and file exists and size > 0)
        import os
        if step_in and os.path.exists(step_in) and os.path.getsize(step_in) > 0:
            model = cq.importers.importStep(step_in)
        else:
            model = cq.Workplane("XY")
            
        result = model

        def append_to_model(base_model, new_shape):
            if len(base_model.objects) == 0:
                return new_shape
            return base_model.union(new_shape)

        # Primitives
        if op_type == 'create_box':
            length = float(params.get('length', 10.0))
            width = float(params.get('width', 10.0))
            height = float(params.get('height', 10.0))
            loc = params.get('origin', [0.0, 0.0, 0.0])
            axis = params.get('axis', [0.0, 0.0, 1.0])
            plane = cq.Plane(origin=cq.Vector(*loc), normal=cq.Vector(*axis))
            primitive = cq.Workplane(plane).box(length, width, height, centered=(True, True, False))
            result = append_to_model(model, primitive)
            
        elif op_type == 'create_cylinder':
            radius = float(params.get('radius', 5.0))
            height = float(params.get('height', 10.0))
            loc = params.get('origin', [0.0, 0.0, 0.0])
            axis = params.get('axis', [0.0, 0.0, 1.0])
            plane = cq.Plane(origin=cq.Vector(*loc), normal=cq.Vector(*axis))
            primitive = cq.Workplane(plane).circle(radius).extrude(height)
            result = append_to_model(model, primitive)

        elif op_type == 'create_cone':
            base_r = float(params.get('base_radius', 5.0))
            top_r = float(params.get('top_radius', 0.0))
            height = float(params.get('height', 10.0))
            loc = params.get('origin', [0.0, 0.0, 0.0])
            axis = params.get('axis', [0.0, 0.0, 1.0])
            plane = cq.Plane(origin=cq.Vector(*loc), normal=cq.Vector(*axis))
            tip = max(top_r, 0.001)
            primitive = cq.Workplane(plane).circle(base_r).workplane(offset=height).circle(tip).loft()
            result = append_to_model(model, primitive)

        elif op_type == 'create_sphere':
            radius = float(params.get('radius', 5.0))
            loc = params.get('origin', [0.0, 0.0, 0.0])
            axis = params.get('axis', [0.0, 0.0, 1.0])
            plane = cq.Plane(origin=cq.Vector(*loc), normal=cq.Vector(*axis))
            primitive = cq.Workplane(plane).sphere(radius)
            result = append_to_model(model, primitive)

        # Booleans
        elif op_type in ('boolean_cut', 'boolean_union', 'boolean_intersect'):
            tool_data = p.get('tool', {})
            tool_type = tool_data.get('type', 'cylinder')
            params = tool_data.get('params', {})
            
            loc = params.get('origin', [0.0, 0.0, 0.0])
            axis = params.get('axis', [0.0, 0.0, 1.0])
            plane = cq.Plane(origin=cq.Vector(*loc), normal=cq.Vector(*axis))
            
            if tool_type == 'box':
                length = float(params.get('length', 10.0))
                width = float(params.get('width', 10.0))
                height = float(params.get('height', 10.0))
                tool = cq.Workplane(plane).box(length, width, height, centered=(True, True, False))
            elif tool_type == 'cylinder':
                radius = float(params.get('radius', 5.0))
                height = float(params.get('height', 10.0))
                tool = cq.Workplane(plane).circle(radius).extrude(height)
            elif tool_type == 'cone':
                base_r = float(params.get('base_radius', 5.0))
                top_r = float(params.get('top_radius', 0.0))
                height = float(params.get('height', 10.0))
                tip = max(top_r, 0.001)
                tool = cq.Workplane(plane).circle(base_r).workplane(offset=height).circle(tip).loft()
            elif tool_type == 'sphere':
                radius = float(params.get('radius', 5.0))
                tool = cq.Workplane(plane).sphere(radius)
            else:
                raise ValueError(f"Unknown tool_type: {tool_type}")
                
            if op_type == 'boolean_cut':
                result = model.cut(tool)
            elif op_type == 'boolean_union':
                # Base model might be empty if we're combining two things, but typically union assumes base exists
                if len(model.objects) == 0:
                    result = tool
                else:
                    result = model.union(tool)
            elif op_type == 'boolean_intersect':
                result = model.intersect(tool)

        # Modifiers
        elif op_type == 'fillet_edges':
            radius = float(params.get('radius', 1.0))
            selector = params.get('selector', '') # e.g. "Z" for vertical edges
            if selector:
                result = model.edges(selector).fillet(radius)
            else:
                result = model.edges().fillet(radius)
                
        elif op_type == 'chamfer_edges':
            length = float(params.get('length', 1.0))
            selector = params.get('selector', '') 
            if selector:
                result = model.edges(selector).chamfer(length)
            else:
                result = model.edges().chamfer(length)
                
        else:
            raise ValueError(f"Unsupported op_type: {op_type}")
            
        # Export
        if len(result.objects) == 0:
            raise ValueError("Operation resulted in an empty shape.")
            
        cq.exporters.export(result, step_out)
        print("SUCCESS")
        
    except Exception as e:
        print(f"ERROR: {str(e)}\\n{traceback.format_exc()}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
"""

class BRepEngineError(Exception):
    pass

class BRepEngine:
    def __init__(self, timeout: int = 45):
        self.timeout = timeout
        config.STEP_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def execute_sequence(self, operations: List[Dict[str, Any]], start_step_path: str = None) -> List[Dict[str, Any]]:
        """
        Executes a sequence of B-Rep operations iteratively.
        Returns a list of outputs, tracking the step file for each state.
        Throws BRepEngineError if a step fails.
        """
        logger.info(f"Starting execution of {len(operations)} B-Rep operations.")
        
        current_step_path = start_step_path
        history = []
        
        for idx, op in enumerate(operations):
            op_id = op.get('step_id', idx + 1)
            op_type = op.get('type')
            logger.info(f"Executing step {op_id}: {op_type}")
            
            out_filename = f"brep_gen_{uuid.uuid4().hex[:8]}.step"
            out_path = config.STEP_OUTPUT_DIR / out_filename
            
            try:
                self._run_isolated_op(op, current_step_path, str(out_path))
                current_step_path = str(out_path)
                
                # Analyze Bounding Box as a quick sanity check
                bbox = self._get_bounding_box(current_step_path)
                
                history.append({
                    'step_id': op_id,
                    'status': 'success',
                    'step_file': current_step_path,
                    'step_url': f'/outputs/step/{out_filename}',
                    'bounding_box': bbox,
                    'operation': op
                })
            except Exception as e:
                logger.error(f"Step {op_id} failed: {str(e)}")
                history.append({
                    'step_id': op_id,
                    'status': 'error',
                    'error': str(e),
                    'operation': op
                })
                raise BRepEngineError(f"Step {op_id} failed: {str(e)}")
                
        return history

    def _run_isolated_op(self, op: dict, step_in: str, step_out: str):
        params = {
            'type': op.get('type'),
            'params': op.get('params', {}),
            'tool': op.get('tool', {}),
            'step_in': step_in,
            'step_out': step_out
        }
        
        params_json = json.dumps(params)
        
        # Use python 3.12 global because CadQuery is there
        python_exe = "C:/Users/Ashfaq Ahamed A/AppData/Local/Programs/Python/Python312/python.exe"
        if not os.path.exists(python_exe):
            python_exe = sys.executable

        try:
            proc = subprocess.run(
                [python_exe, '-c', _BREP_WORKER_SCRIPT, params_json],
                timeout=self.timeout,
                capture_output=True,
                text=True
            )
        except subprocess.TimeoutExpired:
            raise BRepEngineError(f"Operation timed out after {self.timeout}s.")
            
        if proc.returncode != 0 and 'SUCCESS' not in proc.stdout:
            stderr = proc.stderr.strip()
            if not stderr:
                stderr = proc.stdout.strip()
            raise BRepEngineError(f"OCC Crash/Error: {stderr}")

        if not os.path.exists(step_out) or os.path.getsize(step_out) == 0:
            raise BRepEngineError("Subprocess succeeded but output STEP is missing or empty.")

    def _get_bounding_box(self, step_path: str) -> dict:
        import cadquery as cq
        try:
            model = cq.importers.importStep(step_path)
            bb = model.val().BoundingBox()
            return {
                'x_len': round(float(bb.xlen), 3),
                'y_len': round(float(bb.ylen), 3),
                'z_len': round(float(bb.zlen), 3)
            }
        except:
            return {}
