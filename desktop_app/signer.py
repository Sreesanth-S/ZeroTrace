"""
Certificate Signing Utilities
Handles digital signature generation and verification using ECDSA
"""

import json
import hashlib
import base64
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from Crypto.PublicKey import ECC
from Crypto.Signature import DSS
from Crypto.Hash import SHA256
from dotenv import load_dotenv


load_dotenv(Path(__file__).with_name(".env"))


class CertificateSigner:
    """Handle digital signing of certificates"""
    
    def __init__(
        self,
        private_key_path: Optional[str] = None,
        public_key_path: Optional[str] = None,
        private_key_pem: Optional[str] = None,
        public_key_pem: Optional[str] = None
    ):
        # Keep path args for backward compatibility, but prefer environment keys.
        self.private_key_path = Path(private_key_path) if private_key_path else Path("keys/private_key.pem")
        self.public_key_path = Path(public_key_path) if public_key_path else Path("keys/public_key.pem")
        self.private_key_pem = private_key_pem or self._read_env_key("SIGNING_PRIVATE_KEY_PEM")
        self.public_key_pem = public_key_pem or self._read_env_key("SIGNING_PUBLIC_KEY_PEM")

        # Backward-compatible fallback: read legacy key files if env vars are missing.
        if not self.private_key_pem and self.private_key_path.exists():
            with open(self.private_key_path, 'r') as f:
                self.private_key_pem = f.read()

        if not self.public_key_pem and self.public_key_path.exists():
            with open(self.public_key_path, 'r') as f:
                self.public_key_pem = f.read()

        # If neither source exists, generate keys in-memory (do not write folders/files).
        if not self.private_key_pem or not self.public_key_pem:
            self.generate_keys()

    def _read_env_key(self, env_name: str) -> Optional[str]:
        value = os.getenv(env_name)
        if not value:
            return None
        # Support multi-line PEM represented with escaped newlines in .env.
        return value.replace("\\n", "\n")
    
    def generate_keys(self):
        """Generate new ECC key pair in memory"""
        key = ECC.generate(curve='P-256')
        self.private_key_pem = key.export_key(format='PEM')
        self.public_key_pem = key.public_key().export_key(format='PEM')
    
    def load_private_key(self) -> ECC.EccKey:
        """Load private key from environment or fallback source"""
        if not self.private_key_pem:
            raise ValueError("SIGNING_PRIVATE_KEY_PEM is not set")
        return ECC.import_key(self.private_key_pem)
    
    def load_public_key(self) -> ECC.EccKey:
        """Load public key from environment or fallback source"""
        if not self.public_key_pem:
            raise ValueError("SIGNING_PUBLIC_KEY_PEM is not set")
        return ECC.import_key(self.public_key_pem)
    
    def generate_certificate_hash(self, cert_data: Dict) -> str:
        # Remove signature if present to avoid circular dependency
        clean_data = {k: v for k, v in cert_data.items() if k != '_signature'}
        
        # Create deterministic JSON string
        json_str = json.dumps(clean_data, sort_keys=True, separators=(',', ':'))
        
        # Generate hash
        hash_obj = hashlib.sha256(json_str.encode())
        return hash_obj.hexdigest()
    
    def sign_certificate(self, cert_data: Dict) -> Dict:
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
    if not timestamp:
        timestamp = datetime.utcnow().isoformat()
    
    data = f"{device_id}:{timestamp}".encode()
    hash_obj = hashlib.sha256(data)
    return f"CERT-{hash_obj.hexdigest()[:16].upper()}"
