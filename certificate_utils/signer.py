"""
Certificate Signing Utilities
Handles digital signature generation and verification using ECDSA
"""

import json
import hashlib
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from Crypto.PublicKey import ECC
from Crypto.Signature import DSS
from Crypto.Hash import SHA256


class CertificateSigner:
    """Handle digital signing of certificates"""
    
    def __init__(self, private_key_path: Optional[str] = None, public_key_path: Optional[str] = None):
        """
        Initialize the signer with key paths
        
        Args:
            private_key_path: Path to private key file
            public_key_path: Path to public key file
        """
        self.private_key_path = Path(private_key_path) if private_key_path else Path("keys/private_key.pem")
        self.public_key_path = Path(public_key_path) if public_key_path else Path("keys/public_key.pem")
        
        # Ensure keys directory exists
        self.private_key_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load or generate keys
        if not self.private_key_path.exists():
            self.generate_keys()
    
    def generate_keys(self):
        """Generate new ECC key pair"""
        key = ECC.generate(curve='P-256')
        
        # Save private key
        with open(self.private_key_path, 'wb') as f:
            f.write(key.export_key(format='PEM').encode())
        
        # Save public key
        with open(self.public_key_path, 'wb') as f:
            f.write(key.public_key().export_key(format='PEM').encode())
        
        print(f"Generated new key pair at {self.private_key_path}")
    
    def load_private_key(self) -> ECC.EccKey:
        """Load private key from file"""
        with open(self.private_key_path, 'r') as f:
            return ECC.import_key(f.read())
    
    def load_public_key(self) -> ECC.EccKey:
        """Load public key from file"""
        with open(self.public_key_path, 'r') as f:
            return ECC.import_key(f.read())
    
    def generate_certificate_hash(self, cert_data: Dict) -> str:
        """
        Generate SHA-256 hash of certificate data
        
        Args:
            cert_data: Dictionary containing certificate information
            
        Returns:
            Hex string of hash
        """
        # Remove signature if present to avoid circular dependency
        clean_data = {k: v for k, v in cert_data.items() if k != '_signature'}
        
        # Create deterministic JSON string
        json_str = json.dumps(clean_data, sort_keys=True, separators=(',', ':'))
        
        # Generate hash
        hash_obj = hashlib.sha256(json_str.encode())
        return hash_obj.hexdigest()
    
    def sign_certificate(self, cert_data: Dict) -> Dict:
        """
        Sign certificate data and add signature
        
        Args:
            cert_data: Dictionary containing certificate information
            
        Returns:
            Certificate data with signature added
        """
        # Generate hash
        cert_hash = self.generate_certificate_hash(cert_data)
        
        # Load private key
        private_key = self.load_private_key()
        
        # Create signature
        hash_obj = SHA256.new(cert_hash.encode())
        signer = DSS.new(private_key, 'fips-186-3')
        signature = signer.sign(hash_obj)
        
        # Add signature to certificate
        cert_data['_signature'] = {
            'algorithm': 'ECDSA-SHA256',
            'signature': base64.b64encode(signature).decode(),
            'public_key': self.load_public_key().export_key(format='PEM'),
            'signed_at': datetime.utcnow().isoformat() + 'Z',
            'verification_hash': cert_hash
        }
        
        return cert_data
    
    def verify_signature(self, cert_data: Dict) -> bool:
        """
        Verify certificate signature
        
        Args:
            cert_data: Dictionary containing certificate with signature
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Extract signature info
            signature_info = cert_data.get('_signature')
            if not signature_info:
                return False
            
            # Decode signature
            signature = base64.b64decode(signature_info['signature'])
            
            # Get stored hash
            stored_hash = signature_info['verification_hash']
            
            # Calculate current hash
            current_hash = self.generate_certificate_hash(cert_data)
            
            # Check if hash matches
            if stored_hash != current_hash:
                return False
            
            # Load public key from signature or file
            if 'public_key' in signature_info:
                public_key = ECC.import_key(signature_info['public_key'])
            else:
                public_key = self.load_public_key()
            
            # Verify signature
            hash_obj = SHA256.new(stored_hash.encode())
            verifier = DSS.new(public_key, 'fips-186-3')
            verifier.verify(hash_obj, signature)
            
            return True
            
        except Exception as e:
            print(f"Signature verification failed: {e}")
            return False


def generate_cert_id(device_id: str, timestamp: Optional[str] = None) -> str:
    """
    Generate unique certificate ID
    
    Args:
        device_id: Device identifier
        timestamp: Optional timestamp string
        
    Returns:
        Unique certificate ID
    """
    if not timestamp:
        timestamp = datetime.utcnow().isoformat()
    
    data = f"{device_id}:{timestamp}".encode()
    hash_obj = hashlib.sha256(data)
    return f"CERT-{hash_obj.hexdigest()[:16].upper()}"