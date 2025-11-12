"""
Routes package initialization
"""

from flask import Flask
from .auth import auth_bp
from .certificates import certificates_bp
from .verification import verification_bp


def register_blueprints(app: Flask):
    """
    Register all blueprints with the Flask app
    
    Args:
        app: Flask application instance
    """
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(certificates_bp, url_prefix='/api/certificates')
    app.register_blueprint(verification_bp, url_prefix='/api/verify')