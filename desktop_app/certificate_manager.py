import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple
import sys
sys.path.append(str(Path(__file__).parent.parent))

from certificate_utils.signer import CertificateSigner, generate_cert_id
from certificate_utils.pdf_generator import PDFCertificateGenerator
from desktop_app.supabase_client import SupabaseDesktopClient

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class CertificateManager:
    """Manage certificate lifecycle in desktop application"""
    
    def __init__(self, supabase_client: SupabaseDesktopClient):
        """
        Initialize certificate manager
        
        Args:
            supabase_client: Initialized Supabase client
        """
        self.supabase = supabase_client
        self.signer = CertificateSigner()
        self.pdf_generator = PDFCertificateGenerator()
        
        # Local storage paths
        self.local_certs_dir = Path("certificates")
        self.local_certs_dir.mkdir(exist_ok=True)
    
    def create_certificate_data(self, wipe_result: Dict) -> Dict:
        """
        Create certificate data structure from wipe result
        
        Args:
            wipe_result: Result from wipe operation
            
        Returns:
            Certificate data dictionary
        """
        # Generate certificate ID
        device_id = wipe_result.get('device_id', 'unknown')
        cert_id = generate_cert_id(device_id)
        
        # Build certificate data
        cert_data = {
            'cert_id': cert_id,
            'version': '1.0',
            'generated_at': datetime.utcnow().isoformat() + 'Z',
            'device_id': device_id,
            'device': wipe_result.get('device_name', 'Unknown Device'),
            'device_info': {
                'model': wipe_result.get('model', 'N/A'),
                'serial': wipe_result.get('serial', 'N/A'),
                'capacity': wipe_result.get('capacity', 'N/A'),
                'type': wipe_result.get('device_type', 'Unknown')
            },
            'method_used': wipe_result.get('method', 'DoD_3Pass'),
            'passes_completed': wipe_result.get('passes', 3),
            'start': wipe_result.get('start_time', datetime.utcnow().isoformat()),
            'end': wipe_result.get('end_time', datetime.utcnow().isoformat()),
            'status': wipe_result.get('status', 'Completed'),
            'verification': {
                'completion_hash': wipe_result.get('completion_hash', ''),
                'method': 'SHA-256',
                'verified': True
            },
            'operator': {
                'user_id': self.supabase.user.id if self.supabase.user else 'local',
                'email': self.supabase.user.email if self.supabase.user else 'offline'
            }
        }
        
        return cert_data
    
    def generate_and_sign_certificate(self, wipe_result: Dict) -> Tuple[Path, Path, Dict]:
        """
        Generate signed certificate files (JSON and PDF)
        
        Args:
            wipe_result: Result from wipe operation
            
        Returns:
            Tuple of (json_path, pdf_path, cert_data)
        """
        # Create certificate data
        cert_data = self.create_certificate_data(wipe_result)
        
        # Sign certificate
        signed_cert = self.signer.sign_certificate(cert_data)
        
        # Save JSON
        json_filename = f"{signed_cert['cert_id']}.json"
        json_path = self.local_certs_dir / json_filename
        
        with open(json_path, 'w') as f:
            json.dump(signed_cert, f, indent=2)
        
        # Generate PDF
        pdf_path = self.pdf_generator.generate_certificate(signed_cert, json_filename.replace('.json', '.pdf'))
        
        return json_path, pdf_path, signed_cert
    
    def upload_certificate(self, json_path: Path, pdf_path: Path, cert_data: Dict) -> bool:
        """
        Upload certificate to Supabase
        
        Args:
            json_path: Path to JSON certificate
            pdf_path: Path to PDF certificate
            cert_data: Certificate data
            
        Returns:
            True if successful
        """
        if not self.supabase.user:
            print("User not logged in. Certificate saved locally only.")
            return False
        
        try:
            # Upload files
            upload_result = self.supabase.upload_certificate(
                self.supabase.user.id,
                cert_data['cert_id'],
                json_path,
                pdf_path
            )
            
            if not upload_result['success']:
                print(f"Upload failed: {upload_result.get('error')}")
                return False
            
            # Add URLs to cert data
            cert_data['json_url'] = upload_result['json_url']
            cert_data['pdf_url'] = upload_result['pdf_url']
            
            # Insert database record
            record_id = self.supabase.insert_certificate_record(cert_data)
            
            if not record_id:
                print("Failed to create database record")
                return False
            
            print(f"Certificate uploaded successfully. Record ID: {record_id}")
            return True
            
        except Exception as e:
            print(f"Upload error: {e}")
            return False
    
    def process_wipe_completion(self, wipe_result: Dict, auto_upload: bool = True) -> Dict:
        """
        Complete certificate processing after wipe
        
        Args:
            wipe_result: Result from wipe operation
            auto_upload: Whether to automatically upload to Supabase
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Generate and sign certificate
            json_path, pdf_path, cert_data = self.generate_and_sign_certificate(wipe_result)
            
            result = {
                'success': True,
                'json_path': str(json_path),
                'pdf_path': str(pdf_path),
                'cert_id': cert_data['cert_id'],
                'uploaded': False
            }
            
            # Upload if requested and user is logged in
            if auto_upload and self.supabase.user:
                result['uploaded'] = self.upload_certificate(json_path, pdf_path, cert_data)
            
            return result
            
        except Exception as e:
            print(f"Certificate processing error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_local_certificates(self) -> list:
        """
        Get list of locally stored certificates
        
        Returns:
            List of certificate file paths
        """
        return list(self.local_certs_dir.glob("*.json"))
    
    def sync_local_certificates(self) -> Dict:
        """
        Sync local certificates with Supabase
        
        Returns:
            Dictionary with sync results
        """
        if not self.supabase.user:
            return {'success': False, 'message': 'User not logged in'}
        
        local_certs = self.get_local_certificates()
        synced = 0
        failed = 0
        
        for json_path in local_certs:
            try:
                # Load certificate
                with open(json_path, 'r') as f:
                    cert_data = json.load(f)
                
                # Check if already uploaded
                existing = self.supabase.verify_certificate_by_id(cert_data['cert_id'])
                if existing:
                    continue
                
                # Find corresponding PDF
                pdf_path = json_path.with_suffix('.pdf')
                if not pdf_path.exists():
                    failed += 1
                    continue
                
                # Upload
                if self.upload_certificate(json_path, pdf_path, cert_data):
                    synced += 1
                else:
                    failed += 1
                    
            except Exception as e:
                print(f"Sync error for {json_path}: {e}")
                failed += 1
        
        return {
            'success': True,
            'synced': synced,
            'failed': failed,
            'total': len(local_certs)
        }
    def upload_certificate_to_supabase(self, json_path: Path, pdf_path: Path, 
                                    cert_data: Dict, wipe_data: Dict = None) -> bool:
        if not self.supabase.user:
            print("User not logged in. Certificate saved locally only.")
            return False
    
        try:
            # Initialize uploader
            uploader = SupabaseCertificateUploader(self.supabase.client)
            
            # Upload complete certificate
            result = uploader.upload_complete_certificate(
                user_id=self.supabase.user.id,
                cert_id=cert_data['cert_id'],
                json_path=json_path,
                pdf_path=pdf_path,
                cert_data=cert_data,
                wipe_data=wipe_data
            )
            
            if result['success']:
                print(f"Certificate uploaded successfully")
                print(f"  Record ID: {result['record_id']}")
                print(f"  JSON URL: {result['urls']['json_url']}")
                print(f"  PDF URL: {result['urls']['pdf_url']}")
                return True
            else:
                print(f"Upload failed: {result['message']}")
                return False
                
        except Exception as e:
            print(f"Upload error: {e}")
            return False
    
class SupabaseCertificateUploader:
    """Handle certificate uploads to Supabase"""
    
    def __init__(self, supabase_client: Client = None):
        """
        Initialize Supabase uploader
        
        Args:
            supabase_client: Existing Supabase client or None to create new
        """
        if supabase_client:
            self.client = supabase_client
        else:
            url = os.getenv('SUPABASE_URL')
            key = os.getenv('SUPABASE_KEY')
            
            if not url or not key:
                raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
            
            self.client = create_client(url, key)
        
        self.bucket_name = 'certificates'
    
    def upload_certificate_files(self, user_id: str, cert_id: str, 
                                  json_path: Path, pdf_path: Path) -> Tuple[bool, str, Optional[Dict]]:
        """
        Upload certificate JSON and PDF files to Supabase Storage
        
        Args:
            user_id: User ID (from auth.users)
            cert_id: Certificate ID
            json_path: Path to JSON certificate file
            pdf_path: Path to PDF certificate file
            
        Returns:
            Tuple of (success: bool, message: str, urls: Dict or None)
        """
        try:
            # Verify files exist
            if not json_path.exists():
                return False, f"JSON file not found: {json_path}", None
            
            if not pdf_path.exists():
                return False, f"PDF file not found: {pdf_path}", None
            
            # Upload JSON file
            json_remote_path = f"{user_id}/{cert_id}.json"
            
            with open(json_path, 'rb') as f:
                json_data = f.read()
            
            json_response = self.client.storage.from_(self.bucket_name).upload(
                path=json_remote_path,
                file=json_data,
                file_options={
                    "content-type": "application/json",
                    "upsert": "true"  # Overwrite if exists
                }
            )
            
            # Upload PDF file
            pdf_remote_path = f"{user_id}/{cert_id}.pdf"
            
            with open(pdf_path, 'rb') as f:
                pdf_data = f.read()
            
            pdf_response = self.client.storage.from_(self.bucket_name).upload(
                path=pdf_remote_path,
                file=pdf_data,
                file_options={
                    "content-type": "application/pdf",
                    "upsert": "true"
                }
            )
            
            # Get public URLs
            json_url = self.client.storage.from_(self.bucket_name).get_public_url(json_remote_path)
            pdf_url = self.client.storage.from_(self.bucket_name).get_public_url(pdf_remote_path)
            
            urls = {
                'json_url': json_url,
                'pdf_url': pdf_url
            }
            
            return True, "Files uploaded successfully", urls
            
        except Exception as e:
            return False, f"Upload failed: {str(e)}", None
    
    def insert_certificate_record(self, cert_data: Dict, json_url: str, pdf_url: str) -> Tuple[bool, str, Optional[str]]:
        try:
            # Extract user_id from operator info or use current user
            user_id = cert_data.get('operator', {}).get('user_id')
            if not user_id or user_id == 'local':
                # Get current authenticated user
                user = self.client.auth.get_user()
                if user and hasattr(user, 'user') and user.user:
                    user_id = user.user.id
                else:
                    return False, "No authenticated user", None
            
            # Prepare record for database
            record = {
                'user_id': user_id,
                'device_id': cert_data.get('device_id', 'unknown'),
                'cert_id': cert_data.get('cert_id'),
                'device_name': cert_data.get('device'),
                'device_model': cert_data.get('device_info', {}).get('model'),
                'device_serial': cert_data.get('device_info', {}).get('serial'),
                'wipe_method': cert_data.get('method_used'),
                'verification_hash': cert_data.get('verification', {}).get('completion_hash', ''),
                'signature': cert_data.get('_signature', {}).get('signature', ''),
                'status': 'verified',
                'wipe_start_time': cert_data.get('start'),
                'wipe_end_time': cert_data.get('end'),
                'json_url': json_url,
                'pdf_url': pdf_url
            }
            
            # Insert into database
            response = self.client.table('certificates').insert(record).execute()
            
            if response.data and len(response.data) > 0:
                record_id = response.data[0]['id']
                return True, "Certificate record created", record_id
            else:
                return False, "No data returned from insert", None
                
        except Exception as e:
            return False, f"Database insert failed: {str(e)}", None
    
    def insert_wipe_log(self, certificate_id: str, wipe_data: Dict) -> Tuple[bool, str]:
        try:
            # Calculate duration in seconds
            start_time = datetime.fromisoformat(wipe_data.get('start_time', '').replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(wipe_data.get('end_time', '').replace('Z', '+00:00'))
            duration_seconds = int((end_time - start_time).total_seconds())
            
            log_record = {
                'certificate_id': certificate_id,
                'device_id': wipe_data.get('device_id'),
                'wipe_passes': wipe_data.get('passes_completed', 1),
                'bytes_wiped': wipe_data.get('device_size', 0),
                'duration_seconds': duration_seconds,
                'errors': wipe_data.get('error', None)
            }
            
            response = self.client.table('wipe_logs').insert(log_record).execute()
            
            if response.data:
                return True, "Wipe log created"
            else:
                return False, "No data returned from insert"
                
        except Exception as e:
            return False, f"Wipe log insert failed: {str(e)}"
    
    def upload_complete_certificate(self, user_id: str, cert_id: str, json_path: Path, pdf_path: Path, cert_data: Dict, wipe_data: Dict = None) -> Dict:
        result = {
            'success': False,
            'files_uploaded': False,
            'record_created': False,
            'log_created': False,
            'message': '',
            'urls': None,
            'record_id': None
        }
        
        try:
            # Step 1: Upload files
            files_success, files_msg, urls = self.upload_certificate_files(
                user_id, cert_id, json_path, pdf_path
            )
            
            if not files_success:
                result['message'] = f"File upload failed: {files_msg}"
                return result
            
            result['files_uploaded'] = True
            result['urls'] = urls
            
            # Step 2: Insert certificate record
            record_success, record_msg, record_id = self.insert_certificate_record(
                cert_data, urls['json_url'], urls['pdf_url']
            )
            
            if not record_success:
                result['message'] = f"Files uploaded, but database insert failed: {record_msg}"
                return result
            
            result['record_created'] = True
            result['record_id'] = record_id
            
            # Step 3: Insert wipe log (optional)
            if wipe_data and record_id:
                log_success, log_msg = self.insert_wipe_log(record_id, wipe_data)
                result['log_created'] = log_success
                if not log_success:
                    result['message'] = f"Certificate uploaded, but log failed: {log_msg}"
                    result['success'] = True  # Still consider overall success
                    return result
            
            # Complete success
            result['success'] = True
            result['message'] = "Certificate uploaded successfully"
            
            return result
            
        except Exception as e:
            result['message'] = f"Upload workflow failed: {str(e)}"
            return result
    
    def verify_certificate_exists(self, cert_id: str) -> Tuple[bool, Optional[Dict]]:
        try:
            response = self.client.table('certificates')\
                .select('*')\
                .eq('cert_id', cert_id)\
                .single()\
                .execute()
            
            if response.data:
                return True, response.data
            else:
                return False, None
                
        except Exception as e:
            return False, None
    
    def get_user_certificates(self, user_id: str, limit: int = 50) -> Tuple[bool, str, list]:
        try:
            response = self.client.table('certificates')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()
            
            if response.data:
                return True, f"Found {len(response.data)} certificates", response.data
            else:
                return True, "No certificates found", []
                
        except Exception as e:
            return False, f"Query failed: {str(e)}", []

def example_usage():
    """Example of how to use the uploader standalone"""
    
    from pathlib import Path
    import json
    
    # Load certificate data
    cert_json = Path("certificates/CERT-0DB799496157518C.json")
    cert_pdf = Path("certificates/CERT-0DB799496157518C.pdf")
    
    with open(cert_json, 'r') as f:
        cert_data = json.load(f)
    
    # Initialize uploader
    uploader = SupabaseCertificateUploader()
    
    # Get current user
    user = uploader.client.auth.get_user()
    if not user or not user.user:
        print("Not logged in")
        return
    
    user_id = user.user.id
    cert_id = cert_data['cert_id']
    
    # Upload
    result = uploader.upload_complete_certificate(
        user_id=user_id,
        cert_id=cert_id,
        json_path=cert_json,
        pdf_path=cert_pdf,
        cert_data=cert_data
    )
    
    print(f"Upload result: {result}")


if __name__ == "__main__":
    example_usage()