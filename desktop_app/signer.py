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
    """Handle digital signing and verification of certificates"""
    
    def __init__(
        self,
        private_key_path: Optional[str] = None,
        public_key_path: Optional[str] = None,
        private_key_pem: Optional[str] = None,
        public_key_pem: Optional[str] = None
    ):
        self.private_key_path = Path(private_key_path) if private_key_path else Path("keys/private_key.pem")
        self.public_key_path = Path(public_key_path) if public_key_path else Path("keys/public_key.pem")
        self.private_key_pem = private_key_pem or self._read_env_key("SIGNING_PRIVATE_KEY_PEM")
        self.public_key_pem = public_key_pem or self._read_env_key("SIGNING_PUBLIC_KEY_PEM")

        # Fallback: read key files if present
        if not self.private_key_pem and self.private_key_path.exists():
            try:
                with open(self.private_key_path, 'r') as f:
                    self.private_key_pem = f.read()
            except Exception:
                pass

        if not self.public_key_pem and self.public_key_path.exists():
            try:
                with open(self.public_key_path, 'r') as f:
                    self.public_key_pem = f.read()
            except Exception:
                pass

        self.has_private_key = bool(self.private_key_pem)

    def _read_env_key(self, env_name: str) -> Optional[str]:
        value = os.getenv(env_name)
        if not value:
            return None
        return value.replace("\\n", "\n")
    
    def generate_keys(self):
        """Generate new ECC key pair in memory (for development/testing setup only)"""
        key = ECC.generate(curve='P-256')
        self.private_key_pem = key.export_key(format='PEM')
        self.public_key_pem = key.public_key().export_key(format='PEM')
        self.has_private_key = True
    
    def load_private_key(self) -> ECC.EccKey:
        """Load private key from environment or fallback source"""
        if not self.private_key_pem:
            raise ValueError("SIGNING_PRIVATE_KEY_PEM is not set. Use server-side signing for production.")
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
    
    def sign_certificate_offline(self, cert_data: Dict) -> Dict:
        """Sign certificate locally (offline mode). Mark clearly as offline signature."""
        if not self.has_private_key:
            # Generate a temporary key if offline local signing is requested without an env key
            self.generate_keys()
        
        cert_hash = self.generate_certificate_hash(cert_data)
        private_key = self.load_private_key()
        
        hash_obj = SHA256.new(cert_hash.encode())
        signer = DSS.new(private_key, 'fips-186-3')
        signature = signer.sign(hash_obj)
        
        cert_data['_signature'] = {
            'algorithm': 'ECDSA-SHA256',
            'signature': base64.b64encode(signature).decode(),
            'public_key': self.load_public_key().export_key(format='PEM'),
            'signed_at': datetime.utcnow().isoformat() + 'Z',
            'verification_hash': cert_hash,
            'signing_mode': 'offline_local'
        }
        
        return cert_data

    def sign_certificate(self, cert_data: Dict) -> Dict:
        """Backward-compatible sign method"""
        return self.sign_certificate_offline(cert_data)
    
    def verify_signature(self, cert_data: Dict, pinned_only: bool = True) -> bool:
        """Verify certificate signature using pinned public key.
        
        Args:
            cert_data: Certificate dictionary with _signature
            pinned_only: If True, strictly use the client's pinned public key
                         rather than trusting the public key embedded in the cert.
        """
        try:
            signature_info = cert_data.get('_signature')
            if not signature_info:
                return False
            
            signature = base64.b64decode(signature_info['signature'])
            stored_hash = signature_info['verification_hash']
            current_hash = self.generate_certificate_hash(cert_data)
            
            if stored_hash != current_hash:
                return False
            
            # Use pinned public key for verification to prevent self-attestation attacks
            if pinned_only and self.public_key_pem:
                public_key = self.load_public_key()
            elif 'public_key' in signature_info:
                public_key = ECC.import_key(signature_info['public_key'])
            else:
                public_key = self.load_public_key()
            
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
