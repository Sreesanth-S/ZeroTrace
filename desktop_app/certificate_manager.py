import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple
import sys
sys.path.append(str(Path(__file__).parent.parent))

from certificate_utils.signer import CertificateSigner, generate_cert_id
from certificate_utils.pdf_generator import PDFCertificateGenerator
from desktop_app.supabase_client import SupabaseDesktopClient


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