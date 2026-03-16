from flask import Blueprint, request, jsonify
import sys
from pathlib import Path
import json

sys.path.append(str(Path(__file__).parent.parent.parent))

from utils.logger import api_logger
from core import config
from services.template_catalog_service import (
    refresh_catalog,
    build_category_tree,
    templates_by_category_path,
)
from services.template_asset_builder import build_template_assets


bp = Blueprint('templates', __name__)


@bp.route('/', methods=['GET'], strict_slashes=False)
@bp.route('/list', methods=['GET'])
def list_templates():
    try:
        catalog = refresh_catalog(sync_zip=True)
        templates = catalog.get('templates', [])

        payload = []
        for t in templates:
            category = '/'.join(t.get('category_path', []))
            payload.append({
                'id': t.get('template_id'),
                'name': t.get('name'),
                'category': category,
                'description': t.get('description', ''),
                'file': Path(t.get('relative_json_path', '')).name,
                'editable_parameters': t.get('editable_parameters', []),
                'thumbnail_url': t.get('thumbnail_url'),
                'step_url': t.get('step_url'),
                'build_status': t.get('build_status', 'pending'),
            })

        categories = sorted({item['category'] for item in payload if item['category']})

        return jsonify({
            'success': True,
            'templates': payload,
            'count': len(payload),
            'categories': categories,
            'summary': catalog.get('summary', {}),
        }), 200
    except Exception as e:
        api_logger.error(f"Failed to list templates: {e}")
        return jsonify({'error': True, 'message': str(e)}), 500


@bp.route('/catalog', methods=['GET'])
def get_catalog():
    try:
        mode = request.args.get('mode', 'edit')
        catalog = refresh_catalog(sync_zip=True)
        return jsonify({
            'success': True,
            'mode': mode,
            'catalog': catalog,
        }), 200
    except Exception as e:
        api_logger.error(f"Failed to load template catalog: {e}")
        return jsonify({'error': True, 'message': str(e)}), 500


@bp.route('/categories', methods=['GET'])
def get_categories():
    try:
        catalog = refresh_catalog(sync_zip=True)
        tree = build_category_tree(catalog.get('templates', []))
        return jsonify({
            'success': True,
            'categories': tree,
            'summary': catalog.get('summary', {}),
        }), 200
    except Exception as e:
        api_logger.error(f"Failed to load template categories: {e}")
        return jsonify({'error': True, 'message': str(e)}), 500


@bp.route('/by-category/<path:category_path>', methods=['GET'])
def get_templates_by_category(category_path):
    try:
        catalog = refresh_catalog(sync_zip=True)
        templates = templates_by_category_path(catalog.get('templates', []), category_path)
        return jsonify({
            'success': True,
            'category_path': category_path,
            'templates': templates,
            'count': len(templates),
        }), 200
    except Exception as e:
        api_logger.error(f"Failed to load templates by category '{category_path}': {e}")
        return jsonify({'error': True, 'message': str(e)}), 500


@bp.route('/rebuild-assets', methods=['POST'])
def rebuild_assets():
    try:
        payload = request.get_json(silent=True) or {}
        force = bool(payload.get('force', False))
        category_prefix = payload.get('category_prefix')
        template_ids = payload.get('template_ids')
        max_templates = payload.get('max_templates')

        result = build_template_assets(
            force=force,
            category_prefix=category_prefix,
            template_ids=template_ids,
            max_templates=max_templates,
        )
        return jsonify(result), 200
    except Exception as e:
        api_logger.error(f"Failed to rebuild template assets: {e}")
        return jsonify({'error': True, 'message': str(e)}), 500


@bp.route('/asset-status', methods=['GET'])
def asset_status():
    try:
        catalog = refresh_catalog(sync_zip=False)
        failed = [
            {
                'template_id': t.get('template_id'),
                'name': t.get('name'),
                'error': t.get('error'),
            }
            for t in catalog.get('templates', [])
            if t.get('build_status') == 'failed'
        ]
        return jsonify({
            'success': True,
            'summary': catalog.get('summary', {}),
            'failed': failed,
        }), 200
    except Exception as e:
        api_logger.error(f"Failed to fetch template asset status: {e}")
        return jsonify({'error': True, 'message': str(e)}), 500


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


@bp.route('/item/<path:template_id>', methods=['GET'])
def get_template_by_id(template_id):
    template_file = config.TEMPLATES_DIR / f"{template_id}.json"

    if not template_file.exists():
        return jsonify({
            'error': True,
            'message': f'Template not found: {template_id}'
        }), 404

    try:
        with open(template_file, 'r') as f:
            template_data = json.load(f)

        return jsonify({
            'success': True,
            'template': template_data,
            'template_id': template_id,
            'category_path': template_id.split('/')[:-1],
        }), 200

    except Exception as e:
        api_logger.error(f"Failed to load template {template_id}: {e}")
        return jsonify({
            'error': True,
            'message': f'Failed to load template: {str(e)}'
        }), 500
