from flask import Blueprint, request, jsonify
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from services.freecad_instance_generator import FreeCADInstanceGenerator
from utils.logger import api_logger
from utils.errors import SynthoCadError
from core import config


bp = Blueprint('viewer', __name__)


@bp.route('/open', methods=['POST'])
def open_in_freecad():
    """
    Open a STEP file in FreeCAD GUI.
    
    Request Body:
    {
        "step_file": "output.step" or "/absolute/path/to/file.step",
        "freecad_path": "/optional/custom/freecad/path.exe"
    }
    
    Returns:
    {
        "status": "success",
        "message": "STEP file opened in FreeCAD",
        "step_file": "/path/to/file.step"
    }
    """
    try:
        data = request.get_json()
        step_file = data.get('step_file', '')
        freecad_path = data.get('freecad_path', None)
        
        if not step_file:
            return jsonify({
                'status': 'error',
                'error': 'step_file is required'
            }), 400
        
        # Convert to absolute path if relative
        step_path = Path(step_file)
        if not step_path.is_absolute():
            step_path = config.STEP_OUTPUT_DIR / step_file
            
        if not step_path.exists():
            return jsonify({
                'status': 'error',
                'error': f'STEP file not found: {step_path}'
            }), 404
        
        api_logger.info(f"Opening STEP file in FreeCAD: {step_path}")
        
        freecad_instance = FreeCADInstanceGenerator(freecad_path)
        freecad_instance.open_step_file(str(step_path), async_mode=True)
        
        api_logger.info("STEP file opened successfully in FreeCAD")
        
        return jsonify({
            'status': 'success',
            'message': 'STEP file opened in FreeCAD',
            'step_file': str(step_path)
        }), 200
        
    except FileNotFoundError as e:
        api_logger.error(f"File not found: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 404
        
    except RuntimeError as e:
        api_logger.error(f"FreeCAD runtime error: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'hint': 'Make sure FreeCAD is installed or provide freecad_path'
        }), 500
        
    except Exception as e:
        api_logger.error(f"Unexpected error opening FreeCAD: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': f'Failed to open FreeCAD: {str(e)}'
        }), 500


@bp.route('/reload', methods=['POST'])
def reload_in_freecad():
    """
    Reload a STEP file in FreeCAD (closes and reopens).
    
    Request Body:
    {
        "step_file": "output.step",
        "freecad_path": "/optional/custom/freecad/path.exe"
    }
    """
    try:
        data = request.get_json()
        step_file = data.get('step_file', '')
        freecad_path = data.get('freecad_path', None)
        
        if not step_file:
            return jsonify({
                'status': 'error',
                'error': 'step_file is required'
            }), 400
        
        # Convert to absolute path if relative
        step_path = Path(step_file)
        if not step_path.is_absolute():
            step_path = config.STEP_OUTPUT_DIR / step_file
            
        if not step_path.exists():
            return jsonify({
                'status': 'error',
                'error': f'STEP file not found: {step_path}'
            }), 404
        
        api_logger.info(f"Reloading STEP file in FreeCAD: {step_path}")
        
        freecad_instance = FreeCADInstanceGenerator(freecad_path)
        freecad_instance.reload_step_file(str(step_path))
        
        api_logger.info("STEP file reloaded successfully in FreeCAD")
        
        return jsonify({
            'status': 'success',
            'message': 'STEP file reloaded in FreeCAD',
            'step_file': str(step_path)
        }), 200
        
    except FileNotFoundError as e:
        api_logger.error(f"File not found: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 404
        
    except RuntimeError as e:
        api_logger.error(f"FreeCAD runtime error: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500
        
    except Exception as e:
        api_logger.error(f"Unexpected error reloading FreeCAD: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': f'Failed to reload FreeCAD: {str(e)}'
        }), 500


@bp.route('/check', methods=['GET'])
def check_freecad():
    """
    Check if FreeCAD is installed and return its path.
    
    Returns:
    {
        "installed": true/false,
        "path": "/path/to/freecad.exe" or null
    }
    """
    try:
        freecad_instance = FreeCADInstanceGenerator()
        
        return jsonify({
            'installed': freecad_instance.freecad_path is not None,
            'path': freecad_instance.freecad_path
        }), 200
        
    except Exception as e:
        api_logger.error(f"Error checking FreeCAD: {str(e)}")
        return jsonify({
            'installed': False,
            'path': None,
            'error': str(e)
        }), 200
