"""
Flask Application for ZeroTrace Web Portal
"""

import os
import sys
from pathlib import Path
from flask import Flask
from flask_cors import CORS

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from web_portal.backend.config import config
from web_portal.backend.supabase_client import SupabaseFlaskClient
from web_portal.backend.routes import register_blueprints


def create_app(config_name='default'):
    """
    Application factory
    
    Args:
        config_name: Configuration name
        
    Returns:
        Flask application instance
    """
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Ensure required directories exist
    Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True)
    
    # Initialize CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": app.config['CORS_ORIGINS'],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Initialize Supabase
    supabase_client = SupabaseFlaskClient()
    supabase_client.init_app(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Health check endpoint
    @app.route('/health')
    def health():
        return {'status': 'healthy', 'version': app.config['APP_VERSION']}
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Not found'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return {'error': 'Internal server error'}, 500
    
    return app


if __name__ == '__main__':
    env = os.getenv('FLASK_ENV', 'development')
    app = create_app(env)
    app.run(host='0.0.0.0', port=5000, debug=app.config['DEBUG'])