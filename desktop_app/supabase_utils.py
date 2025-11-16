# desktop_app/supabase_utils.py
import os
from typing import Optional, Dict, Tuple
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv
import bcrypt

# Load environment variables
load_dotenv()

class SupabaseManager:
    """Manages all Supabase operations for the desktop application"""
    
    def __init__(self):
        """Initialize Supabase client"""
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_KEY')
        
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")
        
        self.client: Client = create_client(self.url, self.key)
        self.user = None
        self.session = None
    
    def sign_in(self, email: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
        try:
            response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            self.session = response.session
            self.user = response.user
            
            return True, "Login successful", {
                'id': response.user.id,
                'email': response.user.email,
                'metadata': response.user.user_metadata
            }
            
        except Exception as e:
            error_msg = str(e)
            if "Invalid login credentials" in error_msg:
                return False, "Invalid email or password", None
            elif "Email not confirmed" in error_msg:
                return False, "Please verify your email before logging in", None
            else:
                return False, f"Login failed: {error_msg}", None
    
    def sign_up(self, email: str, password: str, full_name: str) -> Tuple[bool, str]:
        try:
            response = self.client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "full_name": full_name
                    }
                }
            })
            
            if response.user:
                # Create user profile
                self.client.table('user_profiles').insert({
                    'id': response.user.id,
                    'full_name': full_name
                }).execute()
                
                return True, "Registration successful! Please check your email to verify your account."
            else:
                return False, "Registration failed. Please try again."
                
        except Exception as e:
            error_msg = str(e)
            if "already registered" in error_msg.lower():
                return False, "This email is already registered"
            else:
                return False, f"Registration failed: {error_msg}"
    
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
    
    def get_current_user(self) -> Optional[Dict]:
        """Get current authenticated user"""
        try:
            response = self.client.auth.get_user()
            if response:
                self.user = response.user
                return {
                    'id': response.user.id,
                    'email': response.user.email,
                    'metadata': response.user.user_metadata
                }
        except:
            pass
        return None
    
    def check_session(self) -> bool:
        """Check if user has valid session"""
        try:
            session = self.client.auth.get_session()
            return session is not None
        except:
            return False
    
    def set_user_pin(self, pin: str) -> Tuple[bool, str]:
        if not self.user:
            return False, "No user logged in"
        
        try:
            # Hash PIN with bcrypt
            pin_hash = bcrypt.hashpw(pin.encode('utf-8'), bcrypt.gensalt())
            
            # Update user profile
            self.client.table('user_profiles').update({
                'pin_hash': pin_hash.decode('utf-8')
            }).eq('id', self.user.id).execute()
            
            return True, "PIN set successfully"
            
        except Exception as e:
            return False, f"Failed to set PIN: {str(e)}"
    
    def verify_user_pin(self, pin: str) -> bool:
        if not self.user:
            return False
        
        try:
            # Get stored PIN hash
            response = self.client.table('user_profiles').select('pin_hash').eq(
                'id', self.user.id
            ).single().execute()
            
            if not response.data or not response.data.get('pin_hash'):
                return False
            
            stored_hash = response.data['pin_hash'].encode('utf-8')
            return bcrypt.checkpw(pin.encode('utf-8'), stored_hash)
            
        except Exception as e:
            print(f"PIN verification error: {e}")
            return False
    
    def has_pin_set(self) -> bool:
        """Check if user has PIN set"""
        if not self.user:
            return False
        
        try:
            response = self.client.table('user_profiles').select('pin_hash').eq(
                'id', self.user.id
            ).single().execute()
            
            return bool(response.data and response.data.get('pin_hash'))
        except:
            return False
    
    def upload_certificate_files(self, cert_id: str, json_path: Path, pdf_path: Path) -> Tuple[bool, str, Optional[Dict]]:
        if not self.user:
            return False, "No user logged in", None
        
        try:
            bucket_name = 'certificates'
            user_folder = f"{self.user.id}"
            
            # Upload JSON
            with open(json_path, 'rb') as f:
                json_file_path = f"{user_folder}/{cert_id}.json"
                self.client.storage.from_(bucket_name).upload(
                    json_file_path,
                    f.read(),
                    {'content-type': 'application/json'}
                )
            
            # Upload PDF
            with open(pdf_path, 'rb') as f:
                pdf_file_path = f"{user_folder}/{cert_id}.pdf"
                self.client.storage.from_(bucket_name).upload(
                    pdf_file_path,
                    f.read(),
                    {'content-type': 'application/pdf'}
                )
            
            # Get public URLs
            json_url = self.client.storage.from_(bucket_name).get_public_url(json_file_path)
            pdf_url = self.client.storage.from_(bucket_name).get_public_url(pdf_file_path)
            
            return True, "Files uploaded successfully", {
                'json_url': json_url,
                'pdf_url': pdf_url
            }
            
        except Exception as e:
            return False, f"Upload failed: {str(e)}", None
    
    def insert_certificate_record(self, cert_data: Dict) -> Tuple[bool, str, Optional[str]]:
        if not self.user:
            return False, "No user logged in", None
        
        try:
            record = {
                'user_id': self.user.id,
                'cert_id': cert_data['cert_id'],
                'device_name': cert_data.get('device_name'),
                'device_model': cert_data.get('device_model'),
                'device_serial': cert_data.get('device_serial'),
                'wipe_method': cert_data.get('wipe_method'),
                'verification_hash': cert_data.get('verification_hash'),
                'signature': cert_data.get('signature'),
                'status': 'verified',
                'wipe_start_time': cert_data.get('wipe_start_time'),
                'wipe_end_time': cert_data.get('wipe_end_time'),
                'pdf_url': cert_data.get('pdf_url'),
                'json_url': cert_data.get('json_url')
            }
            
            response = self.client.table('certificates').insert(record).execute()
            
            if response.data:
                return True, "Certificate record created", response.data[0]['id']
            else:
                return False, "Failed to create record", None
                
        except Exception as e:
            return False, f"Database insert failed: {str(e)}", None
    
    def get_user_certificates(self, limit: int = 50) -> Tuple[bool, str, Optional[list]]:
        if not self.user:
            return False, "No user logged in", None
        
        try:
            response = self.client.table('certificates').select('*').eq(
                'user_id', self.user.id
            ).order('created_at', desc=True).limit(limit).execute()
            
            return True, "Certificates fetched", response.data or []
            
        except Exception as e:
            return False, f"Failed to fetch certificates: {str(e)}", None