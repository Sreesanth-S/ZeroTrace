import os
from pathlib import Path
from typing import Dict, Optional, List
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class SupabaseDesktopClient:
    """Supabase client for desktop application"""
    
    def __init__(self):
        """Initialize Supabase client"""
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_KEY')
        self.service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment")
        
        self.client: Client = create_client(self.url, self.service_role_key)
        self.user = None
        self.session = None
    
    def sign_in(self, email: str, password: str) -> bool:
        try:
            response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            self.session = response.session
            self.user = response.user
            return True
            
        except Exception as e:
            print(f"Sign in error: {e}")
            return False
    
    def sign_up(self, email: str, password: str, full_name: Optional[str] = None) -> bool:
        try:
            response = self.client.auth.sign_up({
                "email": email,
                "password": password
            })
            
            # Create user profile if registration successful
            if response.user and full_name:
                self.create_user_profile(response.user.id, full_name)
            
            return True
            
        except Exception as e:
            print(f"Sign up error: {e}")
            return False
    
    def sign_out(self) -> bool:
        """Sign out current user"""
        try:
            self.client.auth.sign_out()
            self.user = None
            self.session = None
            return True
        except Exception as e:
            print(f"Sign out error: {e}")
            return False
    
    def create_user_profile(self, user_id: str, full_name: str) -> bool:
        try:
            self.client.table('user_profiles').insert({
                'id': user_id,
                'full_name': full_name
            }).execute()
            return True
        except Exception as e:
            print(f"Error creating profile: {e}")
            return False
    
    def upload_certificate(self, user_id: str, cert_id: str, 
                          json_path: Path, pdf_path: Path) -> Dict:
        try:
            bucket_name = os.getenv('CERTIFICATE_BUCKET', 'certificates')
            
            # Upload JSON
            with open(json_path, 'rb') as f:
                json_filename = f"{user_id}/{cert_id}.json"
                json_response = self.client.storage.from_(bucket_name).upload(
                    json_filename,
                    f.read(),
                    {'content-type': 'application/json'}
                )
            
            # Upload PDF
            with open(pdf_path, 'rb') as f:
                pdf_filename = f"{user_id}/{cert_id}.pdf"
                pdf_response = self.client.storage.from_(bucket_name).upload(
                    pdf_filename,
                    f.read(),
                    {'content-type': 'application/pdf'}
                )
            
            # Get public URLs
            json_url = self.client.storage.from_(bucket_name).get_public_url(json_filename)
            pdf_url = self.client.storage.from_(bucket_name).get_public_url(pdf_filename)
            
            return {
                'success': True,
                'json_url': json_url,
                'pdf_url': pdf_url
            }
            
        except Exception as e:
            print(f"Upload error: {e}")
            return {'success': False, 'error': str(e)}
    
    def insert_certificate_record(self, cert_data: Dict) -> Optional[str]:
        try:
            # Prepare record
            record = {
                'user_id': self.user.id if self.user else None,
                'device_id': cert_data.get('device_id'),
                'cert_id': cert_data.get('cert_id'),
                'device_name': cert_data.get('device'),
                'device_model': cert_data.get('device_info', {}).get('model'),
                'device_serial': cert_data.get('device_info', {}).get('serial'),
                'wipe_method': cert_data.get('method_used'),
                'verification_hash': cert_data.get('verification', {}).get('completion_hash'),
                'signature': cert_data.get('_signature', {}).get('signature'),
                'status': 'Verified',
                'wipe_start_time': cert_data.get('start'),
                'wipe_end_time': cert_data.get('end'),
                'pdf_url': cert_data.get('pdf_url'),
                'json_url': cert_data.get('json_url')
            }
            
            response = self.client.table('certificates').insert(record).execute()
            
            if response.data:
                return response.data[0]['id']
            return None
            
        except Exception as e:
            print(f"Database insert error: {e}")
            return None
    
    def get_user_certificates(self, user_id: Optional[str] = None) -> List[Dict]:
        try:
            if not user_id:
                user_id = self.user.id if self.user else None
            
            if not user_id:
                return []
            
            response = self.client.table('certificates')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('created_at', desc=True)\
                .execute()
            
            return response.data if response.data else []
            
        except Exception as e:
            print(f"Error fetching certificates: {e}")
            return []
    
    def verify_certificate_by_id(self, cert_id: str) -> Optional[Dict]:
        try:
            response = self.client.table('certificates')\
                .select('*')\
                .eq('cert_id', cert_id)\
                .single()\
                .execute()
            
            return response.data if response.data else None
            
        except Exception as e:
            print(f"Verification error: {e}")
            return None
    
    def update_certificate_urls(self, cert_id: str, json_url: str, pdf_url: str) -> bool:
        try:
            self.client.table('certificates')\
                .update({'json_url': json_url, 'pdf_url': pdf_url})\
                .eq('cert_id', cert_id)\
                .execute()
            return True
        except Exception as e:
            print(f"Update error: {e}")
            return False