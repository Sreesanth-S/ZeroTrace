"""
Public certificate verification routes
"""

import os
import json
import sys
from pathlib import Path
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

# Add certificate_utils to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from certificate_utils.verifier import CertificateVerifier, VerificationResult

verification_bp = Blueprint('verification', __name__)


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


@verification_bp.route('/id/<cert_id>', methods=['GET'])
def verify_by_id(cert_id):
    """Verify certificate by ID"""
    try:
        # Get client info for logging
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', 'Unknown')
        
        # Fetch certificate from database
        cert_record = current_app.supabase.get_certificate_by_id(cert_id)
        
        if not cert_record:
            # Log verification attempt
            current_app.supabase.insert_verification_log(
                cert_id, 'not_found', ip_address, user_agent
            )
            
            return jsonify({
                'status': 'NotFound',
                'message': 'No certificate found with this ID',
                'cert_id': cert_id
            }), 404
        
        # Check status
        if cert_record.get('status') == 'revoked':
            current_app.supabase.insert_verification_log(
                cert_id, 'revoked', ip_address, user_agent
            )
            
            return jsonify({
                'status': 'Revoked',
                'message': 'This certificate has been revoked',
                'cert_id': cert_id,
                'details': {
                    'device_name': cert_record.get('device_name'),
                    'wipe_date': cert_record.get('created_at')
                }
            })
        
        # Log successful verification
        current_app.supabase.insert_verification_log(
            cert_id, 'verified', ip_address, user_agent
        )
        
        return jsonify({
            'status': 'Verified',
            'message': 'Certificate is valid and authentic',
            'cert_id': cert_id,
            'details': {
                'device_name': cert_record.get('device_name'),
                'device_model': cert_record.get('device_model'),
                'wipe_method': cert_record.get('wipe_method'),
                'wipe_date': cert_record.get('wipe_start_time'),
                'status': cert_record.get('status')
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Verification error: {e}")
        return jsonify({'error': 'Verification failed'}), 500


@verification_bp.route('/file', methods=['POST'])
def verify_by_file():
    """Verify certificate by uploading JSON file"""
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Only JSON and PDF allowed'}), 400
        
        # Save file temporarily
        filename = secure_filename(file.filename)
        upload_path = Path(current_app.config['UPLOAD_FOLDER']) / filename
        file.save(str(upload_path))
        
        try:
            # Initialize verifier
            verifier = CertificateVerifier(
                public_key_path=current_app.config.get('PUBLIC_KEY_PATH')
            )
            
            # Verify file
            is_valid, message, cert_data = verifier.verify_certificate_file(str(upload_path))
            
            if not cert_data:
                return jsonify({
                    'status': 'Invalid',
                    'message': message
                }), 400
            
            # Get cert_id
            cert_id = cert_data.get('cert_id')
            
            # Check against database
            db_record = None
            db_match = False
            
            if cert_id:
                db_record = current_app.supabase.get_certificate_by_id(cert_id)
                if db_record:
                    db_is_valid, db_message = verifier.verify_against_database(cert_data, db_record)
                    db_match = db_is_valid
            
            # Log verification
            ip_address = request.remote_addr
            user_agent = request.headers.get('User-Agent', 'Unknown')
            result_status = 'verified' if is_valid and db_match else 'invalid'
            
            if cert_id:
                current_app.supabase.insert_verification_log(
                    cert_id, result_status, ip_address, user_agent
                )
            
            # Build result
            result = VerificationResult(
                is_valid=is_valid,
                message=message,
                cert_data=cert_data,
                db_match=db_match,
                details={
                    'signature_valid': is_valid,
                    'database_match': db_match,
                    'database_status': db_record.get('status') if db_record else None
                }
            )
            
            return jsonify(result.to_dict())
            
        finally:
            # Clean up uploaded file
            if upload_path.exists():
                upload_path.unlink()
        
    except Exception as e:
        current_app.logger.error(f"File verification error: {e}")
        return jsonify({'error': 'File verification failed'}), 500


@verification_bp.route('/hash', methods=['POST'])
def verify_by_hash():
    """Verify certificate by verification hash"""
    try:
        data = request.get_json()
        
        if not data or 'hash' not in data:
            return jsonify({'error': 'Hash is required'}), 400
        
        verification_hash = data['hash']
        
        # Search by verification hash
        response = current_app.supabase.client.table('certificates')\
            .select('*')\
            .eq('verification_hash', verification_hash)\
            .single()\
            .execute()
        
        if not response.data:
            return jsonify({
                'status': 'NotFound',
                'message': 'No certificate found with this hash'
            }), 404
        
        cert_record = response.data
        
        # Log verification
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', 'Unknown')
        
        current_app.supabase.insert_verification_log(
            cert_record.get('cert_id'), 'verified', ip_address, user_agent
        )
        
        return jsonify({
            'status': 'Verified',
            'message': 'Certificate found and verified',
            'cert_id': cert_record.get('cert_id'),
            'details': {
                'device_name': cert_record.get('device_name'),
                'wipe_method': cert_record.get('wipe_method'),
                'wipe_date': cert_record.get('wipe_start_time')
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Hash verification error: {e}")
        return jsonify({'error': 'Verification failed'}), 500