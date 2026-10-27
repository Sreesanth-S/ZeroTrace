from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple, List
from signer import CertificateSigner, generate_cert_id
from pdf_generator import PDFCertificateGenerator
from supabase import create_client, Client
from supabase_client import set_supabase_auth_token
from dotenv import load_dotenv
from logger import logger
import os
import sys
import json


import urllib.request

sys.path.append(str(Path(__file__).parent.parent))
load_dotenv()

class CertificateManager:
    """Manage certificate lifecycle in desktop application"""
    
    def __init__(self, supabase_client, session=None):
        """
        Initialize certificate manager
        
        Args:
            supabase_client: Initialized Supabase client (SupabaseDesktopClient or Client)
            session: User session object containing access_token
        """
        # Get the underlying client if it's wrapped
        if hasattr(supabase_client, 'client'):
            self.supabase = supabase_client.client  # Use the underlying client
            self.supabase_wrapper = supabase_client  # Keep wrapper for other methods
        else:
            self.supabase = supabase_client
            self.supabase_wrapper = supabase_client
        
        self.session = session or getattr(supabase_client, 'session', None)
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
        
        # Local storage paths - use absolute path based on script location
        script_dir = Path(__file__).parent
        self.local_certs_dir = script_dir / "certificates"
        self.local_certs_dir.mkdir(exist_ok=True)

    def _sign_via_backend(self, cert_data: Dict) -> Optional[Dict]:
        """Request server-side signing from backend Express server if user session exists."""
        try:
            session = None
            if hasattr(self.supabase_wrapper, 'session') and self.supabase_wrapper.session:
                session = self.supabase_wrapper.session
            elif hasattr(self.supabase, 'auth'):
                session = self.supabase.auth.get_session()
            
            token = session.access_token if session else None
            if not token:
                logger.info("No active auth token; proceeding with local offline signing")
                return None
            
            backend_url = os.getenv('BACKEND_URL', 'http://localhost:5000')
            url = f"{backend_url}/api/certificates/sign"
            
            payload = json.dumps({"cert_data": cert_data}).encode('utf-8')
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {token}'
                },
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    resp_data = json.loads(response.read().decode('utf-8'))
                    if resp_data.get('success') and resp_data.get('signed_cert'):
                        logger.info("Successfully obtained server-side signature")
                        return resp_data['signed_cert']
            return None
        except Exception as e:
            logger.warning(f"Server-side signing request failed/bypassed: {e}")
            return None
    
    def create_certificate_data(self, wipe_result: Dict) -> Dict:
        """Create certificate JSON data structure matching schema requirements"""
        cert_id = generate_cert_id(
            wipe_result.get('device_id', 'UNKNOWN'),
            wipe_result.get('start_time', datetime.utcnow().isoformat())
        )
        
        user_id = self.user.id if self.user else "local"
        user_email = self.user.email if self.user else "offline"
        
        cert_data = {
            "cert_id": cert_id,
            "version": "1.0",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "device_id": wipe_result.get('device_id', ''),
            "device": wipe_result.get('device_name', ''),
            "device_info": {
                "model": wipe_result.get('device_model', ''),
                "serial": wipe_result.get('device_serial', ''),
                "capacity": wipe_result.get('device_capacity', ''),
                "type": wipe_result.get('device_type', '')
            },
            "method_used": wipe_result.get('wipe_method', ''),
            "passes_completed": wipe_result.get('passes_completed', 1),
            "start": wipe_result.get('start_time', ''),
            "end": wipe_result.get('end_time', ''),
            "status": "Completed" if wipe_result.get('success') else "Failed",
            "verification": {
                "completion_hash": wipe_result.get('verification_hash', ''),
                "method": "SHA-256",
                "verified": wipe_result.get('success', False)
            },
            "operator": {
                "user_id": user_id,
                "email": user_email
            }
        }
        
        return cert_data
    
    def generate_and_sign_certificate(self, wipe_result: Dict) -> Tuple[Path, Path, Path, Dict]:
        """Generate, sign, and create certificate artifacts including QR code
        
        Returns:
            Tuple of (json_path, pdf_path, qr_path, signed_cert)
        """
        # Create certificate data
        cert_data = self.create_certificate_data(wipe_result)
        
        # Sign certificate: Try server-side signing first, fallback to local signing
        signed_cert = self._sign_via_backend(cert_data)
        if not signed_cert:
            signed_cert = self.signer.sign_certificate_offline(cert_data)
        
        # Save JSON
        json_filename = f"{signed_cert['cert_id']}.json"
        json_path = self.local_certs_dir / json_filename
        
        with open(json_path, 'w') as f:
            json.dump(signed_cert, f, indent=2)
        
        # Generate PDF
        pdf_path = self.pdf_generator.generate_certificate(signed_cert, json_filename.replace('.json', '.pdf'))
        
        # Generate standalone QR code image with verification hash
        verification_hash = signed_cert.get('_signature', {}).get('verification_hash', '')
        if not verification_hash:
            verification_hash = signed_cert.get('verification', {}).get('completion_hash', '')
        
        qr_filename = json_filename.replace('.json', '_qr.png')
        qr_path = self.pdf_generator.generate_qr_code_image(
            cert_id=signed_cert['cert_id'],
            verification_hash=verification_hash,
            device_id=signed_cert.get('device_id', ''),
            method=signed_cert.get('method_used', ''),
            output_name=qr_filename
        )
        
        logger.info(f"Generated certificate artifacts: JSON, PDF, and QR code for {signed_cert['cert_id']}")
        return json_path, pdf_path, qr_path, signed_cert
    
    def upload_certificate(self, json_path: Path, pdf_path: Path, cert_data: Dict, wipe_data: Dict = None) -> bool:
        """
        Upload certificate files and metadata record to Supabase storage and database.
        Delegates to SupabaseCertificateUploader for unified execution.
        """
        if not self.user:
            logger.warning("User not logged in. Certificate saved locally only.")
            return False
        
        if not self.supabase:
            logger.error("Supabase client not available")
            return False
        
        # Ensure bearer token is set on both postgrest and storage clients
        token = None
        if getattr(self, 'session', None) and getattr(self.session, 'access_token', None):
            token = self.session.access_token
        elif hasattr(self, 'supabase_wrapper') and getattr(self.supabase_wrapper, 'session', None):
            token = self.supabase_wrapper.session.access_token
        elif hasattr(self.supabase, 'auth'):
            try:
                sess = self.supabase.auth.get_session()
                if sess and getattr(sess, 'access_token', None):
                    token = sess.access_token
            except Exception:
                pass

        if token:
            set_supabase_auth_token(self.supabase, token)

        try:
            uploader = SupabaseCertificateUploader(self.supabase, session=self.session)
            res = uploader.upload_complete_certificate(
                user_id=self.user.id,
                cert_id=cert_data['cert_id'],
                json_path=Path(json_path),
                pdf_path=Path(pdf_path),
                cert_data=cert_data,
                wipe_data=wipe_data
            )
            if not res.get('success'):
                logger.error(f"Certificate upload failed for {cert_data.get('cert_id')}: {res.get('message')}")
            return res.get('success', False)
        except Exception as e:
            logger.error(f"Certificate upload failed: {e}")
            return False

    def upload_certificate_to_supabase(self, json_path: Path, pdf_path: Path, 
                                        cert_data: Dict, wipe_data: Dict = None) -> bool:
        """Alias for upload_certificate for backward compatibility."""
        return self.upload_certificate(json_path, pdf_path, cert_data, wipe_data)

    def process_wipe_completion(self, wipe_result: Dict, auto_upload: bool = True) -> Dict:
        try:
            json_path, pdf_path, qr_path, cert_data = self.generate_and_sign_certificate(wipe_result)
            
            result = {
                'success': True,
                'json_path': str(json_path),
                'pdf_path': str(pdf_path),
                'qr_path': str(qr_path),
                'cert_id': cert_data['cert_id'],
                'uploaded': False
            }
            
            if auto_upload and self.user and self.supabase:
                result['uploaded'] = self.upload_certificate(json_path, pdf_path, cert_data, wipe_result)
            
            return result
        except Exception as e:
            logger.error(f"Certificate processing error: {e}")
            return {'success': False, 'error': str(e)}

    def get_local_certificates(self) -> List[Path]:
        return list(self.local_certs_dir.glob("*.json"))

    def sync_local_certificates(self) -> Dict:
        """Sync all local certificates to Supabase"""
        if not self.user or not self.supabase:
            return {'success': False, 'message': 'User not logged in or Supabase client unavailable', 'synced': 0, 'failed': 0, 'skipped': 0, 'total': 0}

        # Refresh auth token on postgrest and storage sub-clients using session
        token = None
        if getattr(self, 'session', None) and getattr(self.session, 'access_token', None):
            token = self.session.access_token
        elif hasattr(self, 'supabase_wrapper') and getattr(self.supabase_wrapper, 'session', None):
            token = self.supabase_wrapper.session.access_token
        elif hasattr(self.supabase, 'auth'):
            try:
                sess = self.supabase.auth.get_session()
                if sess and getattr(sess, 'access_token', None):
                    token = sess.access_token
            except Exception as auth_err:
                logger.warning(f"Notice: Could not set auth token during sync: {auth_err}")

        if token:
            set_supabase_auth_token(self.supabase, token)

        local_certs = self.get_local_certificates()
        synced, failed, skipped = 0, 0, 0

        for json_path in local_certs:
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    cert_data = json.load(f)
                
                cert_id = cert_data.get('cert_id')
                pdf_path = json_path.with_suffix('.pdf')
                if not cert_id or not pdf_path.exists():
                    failed += 1
                    continue

                uploader = SupabaseCertificateUploader(self.supabase)
                # Check if certificate already exists in database
                exists, existing_record = uploader.verify_certificate_exists(cert_id)
                if exists:
                    skipped += 1
                    logger.info(f"Skipping certificate {cert_id}: already uploaded")
                    continue

                if self.upload_certificate(json_path, pdf_path, cert_data):
                    synced += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Sync error for {json_path}: {e}")
                failed += 1

        return {'success': True, 'synced': synced, 'failed': failed, 'skipped': skipped, 'total': len(local_certs)}
    
class SupabaseCertificateUploader:
    """Handle certificate uploads to Supabase"""
    
    def __init__(self, supabase_client: Client = None, session=None):
        if supabase_client:
            self.client = supabase_client
        else:
            url = os.getenv('SUPABASE_URL')
            key = os.getenv('SUPABASE_KEY')
            
            if not url or not key:
                raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
            
            self.client = create_client(url, key)
        
        self.session = session
        self.bucket_name = 'certificates'
    
    def _upload_via_backend(self, cert_id: str, json_path: Path, pdf_path: Path, token: str) -> Tuple[bool, str, Optional[Dict]]:
        try:
            import base64
            import urllib.request
            backend_url = os.getenv('BACKEND_URL', 'http://localhost:5000')
            url = f"{backend_url}/api/certificates/upload"
            
            with open(json_path, 'r', encoding='utf-8') as f:
                json_content = json.load(f)
            
            with open(pdf_path, 'rb') as f:
                pdf_base64 = base64.b64encode(f.read()).decode('utf-8')
            
            payload = json.dumps({
                "cert_id": cert_id,
                "json_content": json_content,
                "pdf_base64": pdf_base64
            }).encode('utf-8')
            
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {token}'
                },
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status in (200, 201):
                    data = json.loads(resp.read().decode('utf-8'))
                    if data.get('success') and data.get('urls'):
                        return True, "Files uploaded successfully via backend", data['urls']
            return False, "Backend storage upload failed", None
        except Exception as e:
            return False, f"Backend upload error: {e}", None

    def upload_certificate_files(self, user_id: str, cert_id: str, 
                                  json_path: Path, pdf_path: Path) -> Tuple[bool, str, Optional[Dict]]:
        # Verify files exist
        if not json_path.exists():
            return False, f"JSON file not found: {json_path}", None
        
        if not pdf_path.exists():
            return False, f"PDF file not found: {pdf_path}", None

        token = None
        if getattr(self, 'session', None) and getattr(self.session, 'access_token', None):
            token = self.session.access_token
        elif hasattr(self.client, 'auth'):
            try:
                sess = self.client.auth.get_session()
                if sess and getattr(sess, 'access_token', None):
                    token = sess.access_token
            except Exception:
                pass

        if token:
            set_supabase_auth_token(self.client, token)

        try:
            # Step A: Attempt direct client storage upload
            json_remote_path = f"{user_id}/{cert_id}.json"
            pdf_remote_path = f"{user_id}/{cert_id}.pdf"
            
            with open(json_path, 'rb') as f:
                json_data = f.read()
            with open(pdf_path, 'rb') as f:
                pdf_data = f.read()
            
            self.client.storage.from_(self.bucket_name).upload(
                path=json_remote_path,
                file=json_data,
                file_options={"content-type": "application/json", "upsert": "true"}
            )
            
            self.client.storage.from_(self.bucket_name).upload(
                path=pdf_remote_path,
                file=pdf_data,
                file_options={"content-type": "application/pdf", "upsert": "true"}
            )
            
            json_url = self.client.storage.from_(self.bucket_name).get_public_url(json_remote_path)
            pdf_url = self.client.storage.from_(self.bucket_name).get_public_url(pdf_remote_path)
            
            return True, "Files uploaded successfully", {'json_url': json_url, 'pdf_url': pdf_url}
            
        except Exception as e:
            # Step B: Fallback to backend upload if client storage upload is restricted by RLS
            if token:
                logger.info(f"Direct storage upload notice ({e}), falling back to backend upload service...")
                success, msg, urls = self._upload_via_backend(cert_id, json_path, pdf_path, token)
                if success:
                    return True, msg, urls
            return False, f"Upload failed: {str(e)}", None
            
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
    
    def insert_certificate_record(self, cert_data: Dict, json_url: str, pdf_url: str, target_user_id: str = None) -> Tuple[bool, str, Optional[str]]:
        try:
            # Extract user_id from explicit arg, operator info, or session
            user_id = target_user_id or cert_data.get('operator', {}).get('user_id')
            if not user_id or user_id == 'local':
                if hasattr(self.client, 'auth'):
                    sess = self.client.auth.get_session()
                    if sess and getattr(sess, 'user', None):
                        user_id = sess.user.id
                    else:
                        user = self.client.auth.get_user()
                        if user and hasattr(user, 'user') and user.user:
                            user_id = user.user.id
            
            if not user_id or user_id == 'local':
                return False, "No authenticated user ID available for certificate record", None

            # Refresh postgrest token
            if hasattr(self.client, 'auth'):
                try:
                    sess = self.client.auth.get_session()
                    if sess and getattr(sess, 'access_token', None):
                        set_supabase_auth_token(self.client, sess.access_token)
                except Exception:
                    pass
            
            # Prepare record for database
            record = {
                'user_id': user_id,
                'device_id': cert_data.get('device_id', 'unknown'),
                'cert_id': cert_data.get('cert_id'),
                'device_name': cert_data.get('device') or cert_data.get('device_name'),
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
            
            # Use upsert with on_conflict on cert_id to handle duplicates gracefully
            response = self.client.table('certificates').upsert(record, on_conflict='cert_id').execute()
            
            if response.data and len(response.data) > 0:
                record_id = response.data[0]['id']
                return True, "Certificate record created", record_id
            else:
                return True, "Certificate record upserted", None
                
        except Exception as e:
            return False, f"Database insert failed: {str(e)}", None
    
    def insert_wipe_log(self, certificate_id: str, wipe_data: Dict) -> Tuple[bool, str]:
        try:
            start_str = wipe_data.get('start_time') or wipe_data.get('start') or ''
            end_str = wipe_data.get('end_time') or wipe_data.get('end') or ''
            
            duration_seconds = 0
            if start_str and end_str:
                try:
                    s_clean = str(start_str).replace('Z', '+00:00')
                    e_clean = str(end_str).replace('Z', '+00:00')
                    start_time = datetime.fromisoformat(s_clean)
                    end_time = datetime.fromisoformat(e_clean)
                    duration_seconds = max(0, int((end_time - start_time).total_seconds()))
                except Exception:
                    pass

            log_record = {
                'certificate_id': certificate_id,
                'device_id': wipe_data.get('device_id', 'unknown'),
                'wipe_passes': wipe_data.get('passes_completed') or wipe_data.get('passes') or 1,
                'bytes_wiped': wipe_data.get('bytes_wiped') or wipe_data.get('device_size', 0),
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
                cert_data, urls['json_url'], urls['pdf_url'], target_user_id=user_id
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