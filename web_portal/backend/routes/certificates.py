"""
Certificate management routes
"""

from flask import Blueprint, request, jsonify, current_app, send_file
from .auth import require_auth

certificates_bp = Blueprint('certificates', __name__)


@certificates_bp.route('/', methods=['GET'])
@require_auth
def list_certificates():
    """List user's certificates"""
    try:
        # Get pagination parameters
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Fetch certificates
        certificates = current_app.supabase.get_user_certificates(
            request.user.id,
            limit=limit,
            offset=offset
        )
        
        return jsonify({
            'certificates': certificates,
            'total': len(certificates),
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        current_app.logger.error(f"Certificate list error: {e}")
        return jsonify({'error': 'Failed to fetch certificates'}), 500


@certificates_bp.route('/<cert_id>', methods=['GET'])
@require_auth
def get_certificate(cert_id):
    """Get specific certificate"""
    try:
        # Fetch certificate
        cert = current_app.supabase.get_certificate_by_id(cert_id)
        
        if not cert:
            return jsonify({'error': 'Certificate not found'}), 404
        
        # Verify ownership
        if cert.get('user_id') != request.user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        return jsonify({'certificate': cert})
        
    except Exception as e:
        current_app.logger.error(f"Certificate fetch error: {e}")
        return jsonify({'error': 'Failed to fetch certificate'}), 500


@certificates_bp.route('/<cert_id>/download', methods=['GET'])
@require_auth
def download_certificate(cert_id):
    """Download certificate file"""
    try:
        file_type = request.args.get('type', 'pdf')
        
        if file_type not in ['pdf', 'json']:
            return jsonify({'error': 'Invalid file type'}), 400
        
        # Fetch certificate to verify ownership
        cert = current_app.supabase.get_certificate_by_id(cert_id)
        
        if not cert:
            return jsonify({'error': 'Certificate not found'}), 404
        
        if cert.get('user_id') != request.user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Get signed URL
        url = current_app.supabase.get_certificate_file_url(
            cert['user_id'],
            cert_id,
            file_type
        )
        
        if not url:
            return jsonify({'error': 'File not found'}), 404
        
        return jsonify({'download_url': url})
        
    except Exception as e:
        current_app.logger.error(f"Download error: {e}")
        return jsonify({'error': 'Failed to generate download URL'}), 500


@certificates_bp.route('/<cert_id>', methods=['DELETE'])
@require_auth
def delete_certificate(cert_id):
    """Delete certificate"""
    try:
        # Fetch certificate to verify ownership
        cert = current_app.supabase.get_certificate_by_id(cert_id)
        
        if not cert:
            return jsonify({'error': 'Certificate not found'}), 404
        
        if cert.get('user_id') != request.user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Delete from database
        current_app.supabase.client.table('certificates')\
            .delete()\
            .eq('cert_id', cert_id)\
            .execute()
        
        # Optionally delete files from storage
        # (Storage files will be handled by Supabase policies)
        
        return jsonify({'message': 'Certificate deleted successfully'})
        
    except Exception as e:
        current_app.logger.error(f"Delete error: {e}")
        return jsonify({'error': 'Failed to delete certificate'}), 500


@certificates_bp.route('/stats', methods=['GET'])
@require_auth
def get_stats():
    """Get user's certificate statistics"""
    try:
        # Get all user certificates
        certs = current_app.supabase.get_user_certificates(
            request.user.id,
            limit=1000  # Get all for stats
        )
        
        # Calculate stats
        total = len(certs)
        verified = sum(1 for c in certs if c.get('status') == 'verified')
        pending = sum(1 for c in certs if c.get('status') == 'pending')
        revoked = sum(1 for c in certs if c.get('status') == 'revoked')
        
        # Get wipe methods distribution
        methods = {}
        for cert in certs:
            method = cert.get('wipe_method', 'Unknown')
            methods[method] = methods.get(method, 0) + 1
        
        return jsonify({
            'total_certificates': total,
            'verified': verified,
            'pending': pending,
            'revoked': revoked,
            'wipe_methods': methods
        })
        
    except Exception as e:
        current_app.logger.error(f"Stats error: {e}")
        return jsonify({'error': 'Failed to fetch statistics'}), 500