"""
Certificate Verification Utilities
Handles verification of certificate authenticity and integrity
"""

import json
from pathlib import Path
from typing import Dict, Tuple, Optional
from .signer import CertificateSigner


class CertificateVerifier:
    """Verify certificate authenticity and integrity"""
    
    def __init__(self, public_key_path: Optional[str] = None):
        """
        Initialize verifier
        
        Args:
            public_key_path: Path to public key file
        """
        self.signer = CertificateSigner(public_key_path=public_key_path)
    
    def verify_certificate_file(self, cert_path: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Verify certificate from JSON file
        
        Args:
            cert_path: Path to certificate JSON file
            
        Returns:
            Tuple of (is_valid, message, cert_data)
        """
        try:
            # Load certificate
            with open(cert_path, 'r') as f:
                cert_data = json.load(f)
            
            return self.verify_certificate_data(cert_data)
            
        except FileNotFoundError:
            return False, "Certificate file not found", None
        except json.JSONDecodeError:
            return False, "Invalid certificate format", None
        except Exception as e:
            return False, f"Error reading certificate: {str(e)}", None
    
    def verify_certificate_data(self, cert_data: Dict) -> Tuple[bool, str, Dict]:
        """
        Verify certificate from data dictionary
        
        Args:
            cert_data: Certificate data dictionary
            
        Returns:
            Tuple of (is_valid, message, cert_data)
        """
        # Check if signature exists
        if '_signature' not in cert_data:
            return False, "Certificate is not signed", cert_data
        
        # Verify signature
        if not self.signer.verify_signature(cert_data):
            return False, "Invalid signature - certificate has been tampered with", cert_data
        
        # Verify hash integrity
        signature_info = cert_data['_signature']
        stored_hash = signature_info.get('verification_hash')
        calculated_hash = self.signer.generate_certificate_hash(cert_data)
        
        if stored_hash != calculated_hash:
            return False, "Certificate hash mismatch - data integrity compromised", cert_data
        
        return True, "Certificate is valid and authentic", cert_data
    
    def verify_against_database(self, cert_data: Dict, db_record: Optional[Dict]) -> Tuple[bool, str]:
        """
        Verify certificate against database record
        
        Args:
            cert_data: Certificate data from file/upload
            db_record: Certificate record from database
            
        Returns:
            Tuple of (is_valid, message)
        """
        if not db_record:
            return False, "Certificate not found in database"
        
        # Verify cert_id matches
        if cert_data.get('cert_id') != db_record.get('cert_id'):
            return False, "Certificate ID mismatch"
        
        # Verify verification hash matches
        cert_hash = cert_data.get('verification', {}).get('completion_hash')
        db_hash = db_record.get('verification_hash')
        
        if cert_hash != db_hash:
            return False, "Verification hash mismatch"
        
        # Check revocation status
        if db_record.get('status') == 'revoked':
            return False, "Certificate has been revoked"
        
        return True, "Certificate matches database record"
    
    def extract_pdf_metadata(self, pdf_path: str) -> Optional[Dict]:
        """
        Extract certificate metadata from PDF
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Certificate metadata if found, None otherwise
        """
        # This is a placeholder - in production, you would:
        # 1. Use PyPDF2 or similar to extract custom metadata
        # 2. Look for embedded JSON data
        # 3. Extract QR code and decode data
        
        try:
            # For now, look for accompanying JSON file
            json_path = Path(pdf_path).with_suffix('.json')
            if json_path.exists():
                with open(json_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error extracting PDF metadata: {e}")
        
        return None


class VerificationResult:
    """Container for verification results"""
    
    def __init__(self, is_valid: bool, message: str, cert_data: Optional[Dict] = None, 
                 db_match: bool = False, details: Optional[Dict] = None):
        """
        Initialize verification result
        
        Args:
            is_valid: Whether certificate is valid
            message: Verification message
            cert_data: Certificate data
            db_match: Whether certificate matches database
            details: Additional verification details
        """
        self.is_valid = is_valid
        self.message = message
        self.cert_data = cert_data
        self.db_match = db_match
        self.details = details or {}
    
    def to_dict(self) -> Dict:
        """Convert result to dictionary"""
        return {
            'is_valid': self.is_valid,
            'message': self.message,
            'cert_id': self.cert_data.get('cert_id') if self.cert_data else None,
            'device_id': self.cert_data.get('device_id') if self.cert_data else None,
            'db_match': self.db_match,
            'details': self.details,
            'status': 'Verified' if self.is_valid and self.db_match else 
                     'Invalid' if not self.is_valid else 'NotFound'
        }