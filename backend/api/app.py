from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

# Absolute path to the frontend directory (two levels up from backend/api/)
FRONTEND_DIR = Path(__file__).parent.parent.parent / 'frontend'

from api.routes import generation_routes, parameter_routes, template_routes, viewer_routes, cleanup_routes, edit_routes
from utils.logger import api_logger
from utils.errors import SynthoCadError
from core import config


def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # Register all blueprints
    app.register_blueprint(generation_routes.bp, url_prefix='/api/v1/generate')
    app.register_blueprint(parameter_routes.bp, url_prefix='/api/v1/parameters')
    app.register_blueprint(template_routes.bp, url_prefix='/api/v1/templates')
    app.register_blueprint(viewer_routes.bp, url_prefix='/api/v1/viewer')
    app.register_blueprint(cleanup_routes.bp, url_prefix='/api/v1/cleanup')
    app.register_blueprint(edit_routes.bp, url_prefix='/api/v1/edit')
    
    # ── Serve Frontend ────────────────────────────────────────────────────────
    @app.route('/')
    def serve_index():
        """Serve the SynthoCAD frontend"""
        return send_from_directory(FRONTEND_DIR, 'index.html')

    @app.route('/<path:filename>')
    def serve_frontend_asset(filename):
        """Serve frontend static assets (CSS, JS, images, etc.)"""
        # Don't intercept /api/ or /outputs/ routes
        if filename.startswith('api/') or filename.startswith('outputs/'):
            return jsonify({'error': 'Not found'}), 404
        return send_from_directory(FRONTEND_DIR, filename)

    # Serve static files from outputs directory

    @app.route('/outputs/<path:subpath>/<filename>')
    def serve_output_file(subpath, filename):
        """Serve generated files (JSON, Python, STEP, images) from outputs directory"""
        output_dir = Path(__file__).parent.parent.parent / 'outputs' / subpath
        return send_from_directory(output_dir, filename)
    
    # Run auto cleanup on startup if enabled
    if config.CLEANUP_AUTO_RUN and config.CLEANUP_ENABLED:
        try:
            from services.file_cleanup_service import FileCleanupService
            cleanup_service = FileCleanupService(
                output_dirs={
                    'json': config.JSON_OUTPUT_DIR,
                    'py': config.PY_OUTPUT_DIR,
                    'step': config.STEP_OUTPUT_DIR
                },
                max_age_days=config.CLEANUP_MAX_AGE_DAYS,
                max_files_per_type=config.CLEANUP_MAX_FILES_PER_TYPE,
                logger=api_logger
            )
            result = cleanup_service.cleanup_all(dry_run=False)
            api_logger.info(
                f"Auto cleanup: {result['total_deleted_files']} files, "
                f"{result['total_deleted_size_mb']} MB"
            )
        except Exception as e:
            api_logger.warning(f"Auto cleanup failed: {str(e)}")
    
    @app.errorhandler(SynthoCadError)
    def handle_synthocad_error(error):
        api_logger.error(f"SynthoCad Error: {error.code.value} - {error.message}")
        return jsonify(error.to_dict()), 400
        
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': True, 'message': 'Endpoint not found'}), 404
        
    @app.errorhandler(500)
    def internal_error(error):
        api_logger.error(f"Internal server error: {str(error)}")
        return jsonify({'error': True, 'message': 'Internal server error'}), 500
    
    @app.route('/', methods=['GET'])
    def root():
        return jsonify({
            'service': 'SynthoCAD API',
            'version': '1.0.0',
            'status': 'running',
            'endpoints': {
                'health': '/api/v1/health',
                'generation': '/api/v1/generate',
                'parameters': '/api/v1/parameters',
                'templates': '/api/v1/templates',
                'viewer': '/api/v1/viewer',
                'cleanup': '/api/v1/cleanup',
                'edit': '/api/v1/edit'
            }
        }), 200
        
    @app.route('/api/v1/health', methods=['GET'])
    def health_check():
        return jsonify({'status': 'healthy', 'service': 'SynthoCAD API'}), 200
        
    return app


if __name__ == '__main__':
    app = create_app()
    api_logger.info("Starting SynthoCAD API server...")
    app.run(host='0.0.0.0', port=5000, debug=True)
