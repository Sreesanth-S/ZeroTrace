"""
Authentication routes
"""

from flask import Blueprint, request, jsonify, current_app
from functools import wraps

auth_bp = Blueprint('auth', __name__)


def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid authorization header'}), 401
        
        token = auth_header.split(' ')[1]
        user = current_app.supabase.verify_user_token(token)
        
        if not user:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Add user to request context
        request.user = user
        return f(*args, **kwargs)
    
    return decorated_function


@auth_bp.route('/user', methods=['GET'])
@require_auth
def get_user():
    """Get current user info"""
    return jsonify({
        'user': {
            'id': request.user.id,
            'email': request.user.email,
            'created_at': request.user.created_at
        }
    })


@auth_bp.route('/profile', methods=['GET'])
@require_auth
def get_profile():
    """Get user profile"""
    try:
        response = current_app.supabase.client.table('user_profiles')\
            .select('*')\
            .eq('id', request.user.id)\
            .single()\
            .execute()
        
        if response.data:
            return jsonify({'profile': response.data})
        else:
            return jsonify({'profile': None}), 404
            
    except Exception as e:
        current_app.logger.error(f"Profile fetch error: {e}")
        return jsonify({'error': 'Failed to fetch profile'}), 500


@auth_bp.route('/profile', methods=['PUT'])
@require_auth
def update_profile():
    """Update user profile"""
    try:
        data = request.get_json()
        
        # Validate data
        allowed_fields = ['full_name', 'organization', 'phone']
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not update_data:
            return jsonify({'error': 'No valid fields to update'}), 400
        
        # Update or insert profile
        response = current_app.supabase.client.table('user_profiles')\
            .upsert({
                'id': request.user.id,
                **update_data
            })\
            .execute()
        
        return jsonify({
            'message': 'Profile updated successfully',
            'profile': response.data[0] if response.data else None
        })
        
    except Exception as e:
        current_app.logger.error(f"Profile update error: {e}")
        return jsonify({'error': 'Failed to update profile'}), 500