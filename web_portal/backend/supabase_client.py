"""
Supabase Client for Flask Backend
"""

from typing import Dict, Optional, List
from supabase import create_client, Client
from flask import current_app


class SupabaseFlaskClient:
    """Supabase client wrapper for Flask"""
    
    def __init__(self):
        """Initialize client"""
        self.client: Optional[Client] = None
    
    def init_app(self, app):
        """
        Initialize with Flask app
        
        Args:
            app: Flask application instance
        """
        url = app.config.get('SUPABASE_URL')
        key = app.config.get('SUPABASE_KEY')
        
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be configured")
        
        self.client = create_client(url, key)
        app.supabase = self
    
    def verify_user_token(self, token: str) -> Optional[Dict]:
        """
        Verify user JWT token
        
        Args:
            token: JWT token from Authorization header
            
        Returns:
            User data if valid, None otherwise
        """
        try:
            user = self.client.auth.get_user(token)
            return user.user if user else None
        except Exception as e:
            current_app.logger.error(f"Token verification error: {e}")
            return None
    
    def get_certificate_by_id(self, cert_id: str) -> Optional[Dict]:
        """
        Get certificate by ID
        
        Args:
            cert_id: Certificate ID
            
        Returns:
            Certificate record if found
        """
        try:
            response = self.client.table('certificates')\
                .select('*')\
                .eq('cert_id', cert_id)\
                .single()\
                .execute()
            
            return response.data if response.data else None
            
        except Exception as e:
            current_app.logger.error(f"Database query error: {e}")
            return None
    
    def get_user_certificates(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict]:
        """
        Get certificates for a user
        
        Args:
            user_id: User ID
            limit: Maximum number of records
            offset: Offset for pagination
            
        Returns:
            List of certificate records
        """
        try:
            response = self.client.table('certificates')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('created_at', desc=True)\
                .limit(limit)\
                .offset(offset)\
                .execute()
            
            return response.data if response.data else []
            
        except Exception as e:
            current_app.logger.error(f"Database query error: {e}")
            return []
    
    def insert_verification_log(self, cert_id: str, result: str, 
                               ip_address: str, user_agent: str) -> bool:
        """
        Log verification attempt
        
        Args:
            cert_id: Certificate ID
            result: Verification result
            ip_address: Client IP
            user_agent: Client user agent
            
        Returns:
            True if successful
        """
        try:
            self.client.table('verification_logs').insert({
                'cert_id': cert_id,
                'verification_result': result,
                'ip_address': ip_address,
                'user_agent': user_agent
            }).execute()
            return True
        except Exception as e:
            current_app.logger.error(f"Log insert error: {e}")
            return False
    
    def get_certificate_file_url(self, user_id: str, cert_id: str, file_type: str = 'pdf') -> Optional[str]:
        """
        Get signed URL for certificate file
        
        Args:
            user_id: User ID
            cert_id: Certificate ID
            file_type: File type ('pdf' or 'json')
            
        Returns:
            Signed URL if successful
        """
        try:
            bucket_name = current_app.config.get('CERTIFICATE_BUCKET', 'certificates')
            file_path = f"{user_id}/{cert_id}.{file_type}"
            
            # Get signed URL (valid for 1 hour)
            response = self.client.storage.from_(bucket_name)\
                .create_signed_url(file_path, 3600)
            
            return response.get('signedURL') if response else None
            
        except Exception as e:
            current_app.logger.error(f"Storage URL error: {e}")
            return None
    
    def update_certificate_status(self, cert_id: str, status: str) -> bool:
        """
        Update certificate status
        
        Args:
            cert_id: Certificate ID
            status: New status
            
        Returns:
            True if successful
        """
        try:
            self.client.table('certificates')\
                .update({'status': status})\
                .eq('cert_id', cert_id)\
                .execute()
            return True
        except Exception as e:
            current_app.logger.error(f"Update error: {e}")
            return False
    
    def signup_with_profile(self, email: str, password: str, full_name: str) -> Dict:
        """
        Sign up user and create profile using service key
        
        Args:
            email: User email
            password: User password
            full_name: User full name
            
        Returns:
            Dict with user data and success status
        """
        try:
            # Create service client for admin operations
            service_key = current_app.config.get('SUPABASE_SERVICE_KEY')
            if not service_key:
                raise ValueError("SUPABASE_SERVICE_KEY not configured")
            
            service_client = create_client(
                current_app.config['SUPABASE_URL'], 
                service_key
            )
            
            # Sign up user
            auth_response = service_client.auth.sign_up({
                'email': email,
                'password': password,
                'options': {
                    'data': {
                        'full_name': full_name,
                    }
                }
            })
            
            if auth_response.user:
                # Create user profile
                profile_data = {
                    'id': auth_response.user.id,
                    'full_name': full_name
                }
                
                service_client.table('user_profiles').insert(profile_data).execute()
                
                return {
                    'success': True,
                    'user': {
                        'id': auth_response.user.id,
                        'email': auth_response.user.email,
                        'created_at': auth_response.user.created_at
                    },
                    'message': 'User created successfully. Please check your email to verify your account.'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to create user'
                }
                
        except Exception as e:
            current_app.logger.error(f"Signup error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
