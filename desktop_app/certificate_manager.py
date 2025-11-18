from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple, List
from signer import CertificateSigner, generate_cert_id
from pdf_generator import PDFCertificateGenerator
from supabase import create_client, Client
from dotenv import load_dotenv
from logger import logger
import os
import sys
import json


sys.path.append(str(Path(__file__).parent.parent))
load_dotenv()

class CertificateManager:
    """Manage certificate lifecycle in desktop application"""
    
    def __init__(self, supabase_client):
        """
        Initialize certificate manager
        
        Args:
            supabase_client: Initialized Supabase client (SupabaseDesktopClient or Client)
        """
        # Get the underlying client if it's wrapped
        if hasattr(supabase_client, 'client'):
            self.supabase = supabase_client.client  # Use the underlying client
            self.supabase_wrapper = supabase_client  # Keep wrapper for other methods
        else:
            self.supabase = supabase_client
            self.supabase_wrapper = supabase_client
        
        self.signer = CertificateSigner()
        self.pdf_generator = PDFCertificateGenerator()
        
        # Get current user from auth
        self.user = None
        if self.supabase:
            try:
                user_response = self.supabase.auth.get_user()
                if user_response and hasattr(user_response, 'user'):
                    self.user = user_response.user
            except:
                pass
        
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
        
        # Get user info
        user_id = 'local'
        user_email = 'offline'
        
        if self.user:
            user_id = self.user.id
            user_email = self.user.email if hasattr(self.user, 'email') else 'unknown'
        
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
                'Verified': True
            },
            'operator': {
                'user_id': user_id,
                'email': user_email
            }
        }
        
        return cert_data
    
    def generate_and_sign_certificate(self, wipe_result: Dict) -> Tuple[Path, Path, Dict]:
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
        Upload certificate to Supabase storage and database
        
        Args:
            json_path: Path to JSON certificate
            pdf_path: Path to PDF certificate
            cert_data: Certificate data dictionary
            
        Returns:
            True if successful
        """
        if not self.user:
            logger.warning("User not logged in. Certificate saved locally only.")
            return False
        
        if not self.supabase:
            logger.error("Supabase client not available")
            return False
        
        try:
            # Upload files to storage
            bucket_name = 'certificates'
            user_folder = self.user.id
            cert_id = cert_data['cert_id']
            
            logger.info(f"Uploading certificate {cert_id} for user {user_folder}")
            
            # Upload JSON file
            json_remote_path = f"{user_folder}/{cert_id}.json"
            with open(json_path, 'rb') as f:
                json_data = f.read()
            
            try:
                # Use the underlying client's storage API
                json_response = self.supabase.storage.from_(bucket_name).upload(
                    path=json_remote_path,
                    file=json_data,
                    file_options={
                        "content-type": "application/json",
                        "upsert": "true"
                    }
                )
                logger.info(f"✓ JSON uploaded: {json_remote_path}")
            except Exception as e:
                logger.error(f"✗ JSON upload failed: {e}")
                return False
            
            # Upload PDF file
            pdf_remote_path = f"{user_folder}/{cert_id}.pdf"
            with open(pdf_path, 'rb') as f:
                pdf_data = f.read()
            
            try:
                pdf_response = self.supabase.storage.from_(bucket_name).upload(
                    path=pdf_remote_path,
                    file=pdf_data,
                    file_options={
                        "content-type": "application/pdf",
                        "upsert": "true"
                    }
                )
                logger.info(f"✓ PDF uploaded: {pdf_remote_path}")
            except Exception as e:
                logger.error(f"✗ PDF upload failed: {e}")
                return False
            
            # Get public URLs
            json_url = self.supabase.storage.from_(bucket_name).get_public_url(json_remote_path)
            pdf_url = self.supabase.storage.from_(bucket_name).get_public_url(pdf_remote_path)
            
            logger.info(f"✓ URLs generated")
            
            # Insert database record
            try:
                record = {
                    'user_id': self.user.id,
                    'device_id': cert_data.get('device_id', 'unknown'),
                    'cert_id': cert_data['cert_id'],
                    'device_name': cert_data.get('device', 'Unknown'),
                    'device_model': cert_data.get('device_info', {}).get('model', 'N/A'),
                    'device_serial': cert_data.get('device_info', {}).get('serial', 'N/A'),
                    'wipe_method': cert_data.get('method_used', 'Unknown'),
                    'verification_hash': cert_data.get('verification', {}).get('completion_hash', ''),
                    'signature': cert_data.get('_signature', {}).get('signature', ''),
                    'status': 'Verified',
                    'wipe_start_time': cert_data.get('start'),
                    'wipe_end_time': cert_data.get('end'),
                    'json_url': json_url,
                    'pdf_url': pdf_url
                }
                
                response = self.supabase.table('certificates').insert(record).execute()
                
                if response.data:
                    logger.info(f"✓ Certificate record created: {response.data[0]['id']}")
                    return True
                else:
                    logger.error("✗ Database insert returned no data")
                    return False
                    
            except Exception as e:
                logger.error(f"✗ Database insert failed: {e}")
                return False
            
        except Exception as e:
            logger.error(f"✗ Upload error: {e}")
            import traceback
            traceback.print_exc()
            return False


    def process_wipe_completion(self, wipe_result: Dict, auto_upload: bool = True) -> Dict:
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
        return list(self.local_certs_dir.glob("*.json"))
  
    def sync_local_certificates(self) -> Dict:
        """
        Sync all local certificates to Supabase
        
        Returns:
            Dictionary with sync results
        """
        if not self.user:
            return {
                'success': False,
                'message': 'User not logged in',
                'synced': 0,
                'failed': 0,
                'skipped': 0,
                'total': 0
            }
        
        if not self.supabase:
            return {
                'success': False,
                'message': 'Supabase client not available',
                'synced': 0,
                'failed': 0,
                'skipped': 0,
                'total': 0
            }
        
        logger.info("Starting certificate sync...")
        
        local_certs = self.get_local_certificates()
        synced = 0
        failed = 0
        skipped = 0
        
        if not local_certs:
            logger.info("No local certificates to sync")
            return {
                'success': True,
                'message': 'No certificates to sync',
                'synced': 0,
                'failed': 0,
                'skipped': 0,
                'total': 0
            }
        
        logger.info(f"Found {len(local_certs)} local certificates")
        
        for json_path in local_certs:
            try:
                logger.info(f"Processing: {json_path.name}")
                
                # Load certificate data
                with open(json_path, 'r') as f:
                    cert_data = json.load(f)
                
                cert_id = cert_data.get('cert_id')
                if not cert_id:
                    logger.warning(f"No cert_id in {json_path.name}, skipping")
                    failed += 1
                    continue
                
                # Check if already uploaded using self.supabase
                try:
                    existing = self.supabase.table('certificates')\
                        .select('id')\
                        .eq('cert_id', cert_id)\
                        .execute()
                    
                    if existing.data and len(existing.data) > 0:
                        logger.info(f"Certificate {cert_id} already exists, skipping")
                        skipped += 1
                        continue
                except Exception as check_error:
                    logger.warning(f"Could not check existing certificate: {check_error}")
                    # Continue anyway to attempt upload
                
                # Find corresponding PDF
                pdf_path = json_path.with_suffix('.pdf')
                if not pdf_path.exists():
                    logger.warning(f"PDF not found for {json_path.name}")
                    failed += 1
                    continue
                
                # Upload certificate
                logger.info(f"Uploading certificate {cert_id}...")
                if self.upload_certificate(json_path, pdf_path, cert_data):
                    logger.info(f"✓ Synced: {cert_id}")
                    synced += 1
                else:
                    logger.error(f"✗ Failed to sync: {cert_id}")
                    failed += 1
                    
            except Exception as e:
                logger.error(f"Sync error for {json_path}: {e}")
                import traceback
                traceback.print_exc()
                failed += 1
        
        result = {
            'success': True,
            'message': f'Synced {synced} certificates',
            'synced': synced,
            'failed': failed,
            'skipped': skipped,
            'total': len(local_certs)
        }
        
        logger.info(f"Sync complete: {result}")
        return result
    
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
                'status': 'Verified',
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