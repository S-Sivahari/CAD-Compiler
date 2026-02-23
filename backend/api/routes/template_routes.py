from flask import Blueprint, request, jsonify
import sys
from pathlib import Path
import json

sys.path.append(str(Path(__file__).parent.parent.parent))

from utils.logger import api_logger
from core import config


bp = Blueprint('templates', __name__)


@bp.route('/', methods=['GET'], strict_slashes=False)
@bp.route('/list', methods=['GET'])
def list_templates():
    
    templates = []
    
    for category in ['basic', 'mechanical', 'patterns']:
        category_dir = config.TEMPLATES_DIR / category
        if category_dir.exists():
            for json_file in category_dir.glob('*.json'):
                try:
                    with open(json_file, 'r') as f:
                        template_data = json.load(f)
                        
                    templates.append({
                        'id': json_file.stem,
                        'name': template_data.get('final_name', json_file.stem),
                        'category': category,
                        'description': template_data.get('_description', template_data.get('description', '')),
                        'file': json_file.name,
                        'editable_parameters': template_data.get('_editable_parameters', [])
                    })
                except Exception as e:
                    api_logger.warning(f"Failed to load template {json_file}: {e}")
                    
    return jsonify({
        'success': True,
        'templates': templates,
        'count': len(templates),
        'categories': ['basic', 'mechanical', 'patterns']
    }), 200


@bp.route('/<category>/<template_id>', methods=['GET'])
def get_template(category, template_id):
    
    template_file = config.TEMPLATES_DIR / category / f"{template_id}.json"
    
    if not template_file.exists():
        return jsonify({
            'error': True,
            'message': f'Template not found: {category}/{template_id}'
        }), 404
        
    try:
        with open(template_file, 'r') as f:
            template_data = json.load(f)
            
        api_logger.info(f"Loaded template: {category}/{template_id}")
        
        return jsonify({
            'success': True,
            'template': template_data,
            'id': template_id,
            'category': category
        }), 200
        
    except Exception as e:
        api_logger.error(f"Failed to load template {category}/{template_id}: {e}")
        return jsonify({
            'error': True,
            'message': f'Failed to load template: {str(e)}'
        }), 500
