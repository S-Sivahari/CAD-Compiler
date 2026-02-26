from flask import Blueprint, request, jsonify, send_file
import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from services.parameter_extractor import ParameterExtractor
from services.ai_parameter_extractor import AIParameterExtractor
from services.intelligent_parameter_extractor import IntelligentParameterExtractor
from services.parameter_updater import ParameterUpdater
from core.main import SynthoCadPipeline
from utils.logger import api_logger
from utils.errors import ParameterUpdateError
from core import config

bp = Blueprint('parameters', __name__)
extractor = ParameterExtractor()  # AST-based (default, most reliable)
ai_extractor = AIParameterExtractor()  # AI-powered (LLM fallback)
intelligent_extractor = IntelligentParameterExtractor()  # Rule-based JSON parser
updater = ParameterUpdater()
pipeline = SynthoCadPipeline(rag_provider=config.get_rag_provider())


@bp.route('/extract/<filename>', methods=['GET'])
def extract_parameters(filename):
    """
    Extract parameters from generated CadQuery Python file.
    Query params:
    - method: 'legacy' (default, AST-based), 'ai', 'intelligent'
    """
    
    method = request.args.get('method', 'legacy')
    
    # Find corresponding files
    base_name = filename.replace('_generated.py', '')
    json_file = config.JSON_OUTPUT_DIR / f"{base_name}.json"
    py_file = config.PY_OUTPUT_DIR / filename
    
    try:
        # Choose extraction method
        if method == 'ai':
            if not json_file.exists():
                return jsonify({'error': True, 'message': f'JSON file not found: {base_name}.json'}), 404
            params_data = ai_extractor.extract_with_fallback(
                str(json_file), 
                str(py_file) if py_file.exists() else None
            )
            markdown = ai_extractor.generate_markdown(params_data)
        
        elif method == 'intelligent':
            if not json_file.exists():
                return jsonify({'error': True, 'message': f'JSON file not found: {base_name}.json'}), 404
            params_data = intelligent_extractor.extract_from_json(str(json_file))
            markdown = "# Parameters\n\n" + json.dumps(params_data['parameters'], indent=2)
        
        else:
            # AST-based extraction (default — fast, reliable, no LLM needed)
            if not py_file.exists():
                return jsonify({
                    'error': True,
                    'message': f'Python file not found: {filename}'
                }), 404
            params_data = extractor.extract_from_python(str(py_file))
            markdown = extractor.generate_markdown(params_data)
        
        api_logger.info(
            f"Extracted {params_data.get('total_count', 0)} parameters from {base_name} "
            f"using {params_data.get('extraction_method', method)} method"
        )
        
        return jsonify({
            'success': True,
            'file': filename,
            'parameters': params_data.get('parameters', []),
            'markdown': markdown,
            'total_count': params_data.get('total_count', 0),
            'shape_type': params_data.get('shape_type', 'Unknown'),
            'design_intent': params_data.get('design_intent', ''),
            'extraction_method': params_data.get('extraction_method', method),
            'units': params_data.get('units', 'mm')
        }), 200
        
    except Exception as e:
        api_logger.error(f"Parameter extraction failed: {str(e)}")
        return jsonify({
            'error': True,
            'message': f'Failed to extract parameters: {str(e)}'
        }), 500


@bp.route('/update/<filename>', methods=['POST'])
def update_parameters(filename):
    
    py_file = config.PY_OUTPUT_DIR / filename
    
    if not py_file.exists():
        return jsonify({
            'error': True,
            'message': f'Python file not found: {filename}'
        }), 404
        
    data = request.get_json()
    parameters = data.get('parameters', {})
    
    if not parameters:
        raise ParameterUpdateError("No parameters provided for update")
        
    try:
        for param_name, value in parameters.items():
            is_valid, error_msg = updater.validate_parameter_value(param_name, value)
            if not is_valid:
                raise ParameterUpdateError(f"Invalid value for {param_name}: {error_msg}")
                
        success = updater.update_python_file(str(py_file), parameters)
        
        if not success:
            raise ParameterUpdateError("Failed to update Python file")
            
        api_logger.info(f"Updated {len(parameters)} parameters in {filename}")
        
        return jsonify({
            'success': True,
            'message': f'Updated {len(parameters)} parameters',
            'file': filename,
            'updated_parameters': list(parameters.keys())
        }), 200
        
    except ParameterUpdateError as e:
        raise e
    except Exception as e:
        api_logger.error(f"Parameter update failed: {str(e)}")
        return jsonify({
            'error': True,
            'message': f'Failed to update parameters: {str(e)}'
        }), 500


@bp.route('/regenerate/<filename>', methods=['POST'])
def regenerate_step(filename):
    """
    Regenerate STEP file after parameter updates.
    
    Request Body:
    {
        "parameters": {"radius": 15.0, "height": 30.0}
    }
    """
    py_file = config.PY_OUTPUT_DIR / filename
    
    if not py_file.exists():
        return jsonify({
            'error': True,
            'message': f'Python file not found: {filename}'
        }), 404
        
    data = request.get_json()
    parameters = data.get('parameters', {})
    
    if not parameters:
        return jsonify({
            'error': True,
            'message': 'No parameters provided for update'
        }), 400
        
    try:
        # Validate and update parameters
        for param_name, value in parameters.items():
            is_valid, error_msg = updater.validate_parameter_value(param_name, value)
            if not is_valid:
                raise ParameterUpdateError(f"Invalid value for {param_name}: {error_msg}")
                
        updater.update_python_file(str(py_file), parameters)
        
        # Extract output name from filename (remove _generated.py suffix)
        output_name = filename.replace('_generated.py', '').replace('.py', '')
        
        # Regenerate STEP file
        api_logger.info(f"Regenerating {output_name} with updated parameters")
        step_file = pipeline.regenerate_from_updated_python(
            str(py_file), 
            output_name,
            open_freecad=False
        )
        
        api_logger.info(f"Successfully regenerated: {step_file}")

        # Check for GLB (optional — may not exist)
        glb_url = None
        try:
            from core import config as cfg
            glb_dir = getattr(cfg, 'GLB_OUTPUT_DIR', None)
            if glb_dir:
                glb_file = glb_dir / f"{output_name}.glb"
                if glb_file.exists():
                    glb_url = f'/outputs/glb/{output_name}.glb'
        except Exception:
            pass
        
        return jsonify({
            'success': True,
            'status': 'success',
            'message': f'Regenerated with {len(parameters)} updated parameters',
            'py_file': str(py_file),
            'step_file': step_file,
            'glb_url': glb_url,
            'updated_parameters': list(parameters.keys())
        }), 200
        
    except ParameterUpdateError as e:
        api_logger.error(f"Parameter update error: {e.message}")
        return jsonify({
            'error': True,
            'message': e.message
        }), 400
    except Exception as e:
        api_logger.error(f"Regeneration failed: {str(e)}")
        return jsonify({
            'error': True,
            'message': f'Failed to regenerate: {str(e)}'
        }), 500


@bp.route('/view/json/<filename>', methods=['GET'])
def view_json_file(filename):
    """View JSON file contents"""
    
    base_name = filename.replace('.json', '')
    json_file = config.JSON_OUTPUT_DIR / f"{base_name}.json"
    
    if not json_file.exists():
        return jsonify({
            'error': True,
            'message': f'JSON file not found: {filename}'
        }), 404
    
    try:
        with open(json_file, 'r') as f:
            json_data = json.load(f)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'content': json_data,
            'content_str': json.dumps(json_data, indent=2),
            'file_path': str(json_file)
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': True,
            'message': f'Failed to read JSON file: {str(e)}'
        }), 500


@bp.route('/view/python/<filename>', methods=['GET'])
def view_python_file(filename):
    """View generated Python file contents"""
    
    py_file = config.PY_OUTPUT_DIR / filename
    
    if not py_file.exists():
        return jsonify({
            'error': True,
            'message': f'Python file not found: {filename}'
        }), 404
    
    try:
        with open(py_file, 'r') as f:
            code = f.read()
        
        return jsonify({
            'success': True,
            'filename': filename,
            'content': code,
            'file_path': str(py_file),
            'language': 'python'
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': True,
            'message': f'Failed to read Python file: {str(e)}'
        }), 500


@bp.route('/view/step/<filename>', methods=['GET'])
def view_step_file(filename):
    """View or download STEP file"""
    
    base_name = filename.replace('.step', '')
    step_file = config.STEP_OUTPUT_DIR / f"{base_name}.step"
    
    if not step_file.exists():
        return jsonify({
            'error': True,
            'message': f'STEP file not found: {filename}'
        }), 404
    
    # Check if user wants to download or just view metadata
    download = request.args.get('download', 'false').lower() == 'true'
    
    if download:
        return send_file(
            step_file,
            as_attachment=True,
            download_name=filename,
            mimetype='application/step'
        )
    
    try:
        # Read file info
        file_size = step_file.stat().st_size
        
        with open(step_file, 'r') as f:
            content = f.read()
        
        # Extract basic STEP metadata
        lines = content.split('\n')
        header_lines = [l for l in lines if l.startswith('FILE_')]
        
        return jsonify({
            'success': True,
            'filename': filename,
            'file_path': str(step_file),
            'file_size_bytes': file_size,
            'file_size_kb': round(file_size / 1024, 2),
            'content_preview': content[:500] + '...' if len(content) > 500 else content,
            'header': header_lines,
            'download_url': f'/api/v1/parameters/view/step/{filename}?download=true'
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': True,
            'message': f'Failed to read STEP file: {str(e)}'
        }), 500


@bp.route('/list-files', methods=['GET'])
def list_generated_files():
    """List all generated files (JSON, Python, STEP)"""
    
    try:
        json_files = [f.name for f in config.JSON_OUTPUT_DIR.glob('*.json')]
        py_files = [f.name for f in config.PY_OUTPUT_DIR.glob('*.py')]
        step_files = [f.name for f in config.STEP_OUTPUT_DIR.glob('*.step')]
        
        # Group by base name
        all_bases = set()
        for jf in json_files:
            all_bases.add(jf.replace('.json', ''))
        
        files_grouped = []
        for base in sorted(all_bases):
            json_exists = f"{base}.json" in json_files
            py_exists = f"{base}_generated.py" in py_files
            step_exists = f"{base}.step" in step_files
            
            files_grouped.append({
                'base_name': base,
                'json_file': f"{base}.json" if json_exists else None,
                'py_file': f"{base}_generated.py" if py_exists else None,
                'step_file': f"{base}.step" if step_exists else None,
                'complete': json_exists and py_exists and step_exists
            })
        
        return jsonify({
            'success': True,
            'files': files_grouped,
            'total': len(files_grouped),
            'json_count': len(json_files),
            'py_count': len(py_files),
            'step_count': len(step_files)
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': True,
            'message': f'Failed to list files: {str(e)}'
        }), 500
