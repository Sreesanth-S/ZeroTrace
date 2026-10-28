"""
Cryptographic Service for ZeroTrace Backend
Sole authority for digital signing and verification using ECDSA-SHA256 on P-256.
"""

import json
import hashlib
import base64
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
from Crypto.PublicKey import ECC
from Crypto.Signature import DSS
from Crypto.Hash import SHA256

from backend.app.core.config import settings
from backend.app.core.errors import CryptographicError


class CryptoService:
    def __init__(self, private_key_pem: Optional[str] = None, public_key_pem: Optional[str] = None):
        self.private_key_pem = private_key_pem or settings.get_private_key_pem()
        self.public_key_pem = public_key_pem or settings.get_public_key_pem()

    def canonicalize(self, value: Any) -> Any:
        """Deterministically sort dictionary keys for canonical JSON encoding."""
        if isinstance(value, dict):
            return {k: self.canonicalize(v) for k, v in sorted(value.items())}
        if isinstance(value, list):
            return [self.canonicalize(v) for v in value]
        return value

    def compute_certificate_hash(self, cert_data: Dict[str, Any]) -> str:
        """Compute SHA-256 hex digest of the canonical certificate payload without _signature."""
        clean_data = {k: v for k, v in cert_data.items() if k != "_signature"}
        canonical = self.canonicalize(clean_data)
        json_str = json.dumps(canonical, separators=(',', ':'), ensure_ascii=False)
        return hashlib.sha256(json_str.encode('utf-8')).hexdigest().lower()

    def sign_certificate_payload(self, cert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sign canonical certificate payload with backend's authoritative ECDSA private key."""
        if not self.private_key_pem:
            raise CryptographicError("Authoritative private key is not configured on the backend")

        try:
            cert_hash = self.compute_certificate_hash(cert_data)
            private_key = ECC.import_key(self.private_key_pem)

            hash_obj = SHA256.new(cert_hash.encode('utf-8'))
            signer = DSS.new(private_key, 'fips-186-3')
            signature = signer.sign(hash_obj)
            signature_b64 = base64.b64encode(signature).decode('ascii')

            cert_data["_signature"] = {
                "algorithm": "ECDSA-SHA256",
                "signature": signature_b64,
                "public_key": self.public_key_pem,
                "signed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "verification_hash": cert_hash,
                "signing_mode": "backend_authoritative",
                "signing_key_id": settings.SIGNING_KEY_ID
            }
            return cert_data
        except Exception as exc:
            raise CryptographicError(f"Failed to sign certificate payload: {exc}")

    def verify_certificate_signature(
        self,
        cert_data: Dict[str, Any],
        use_authoritative_key_only: bool = True
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Verify both data integrity (canonical hash) and ECDSA cryptographic authenticity.
        Returns (is_valid, reason, debug_info).
        """
        signature_info = cert_data.get("_signature")
        if not signature_info or not isinstance(signature_info, dict):
            return False, "missing_signature_object", {}

        stored_hash = str(
            signature_info.get("verification_hash") or
            (cert_data.get("verification") or {}).get("completion_hash") or
            ""
        ).strip().lower()

        signature_b64 = signature_info.get("signature")
        if not stored_hash or not signature_b64:
            return False, "missing_signature_fields", {}

        # 1. Integrity check: computed canonical hash must match stored verification_hash
        calculated_hash = self.compute_certificate_hash(cert_data)
        if stored_hash != calculated_hash:
            return False, "hash_mismatch", {
                "stored_hash": stored_hash,
                "calculated_hash": calculated_hash
            }

        # 2. Cryptographic Authenticity check
        key_to_use_pem = self.public_key_pem if use_authoritative_key_only else (
            self.public_key_pem or signature_info.get("public_key")
        )
        if not key_to_use_pem:
            return False, "missing_public_key", {}

        try:
            public_key = ECC.import_key(key_to_use_pem)
            signature_bytes = base64.b64decode(signature_b64)
            hash_obj = SHA256.new(stored_hash.encode('utf-8'))
            verifier = DSS.new(public_key, 'fips-186-3')
            verifier.verify(hash_obj, signature_bytes)
            return True, "ok", {
                "stored_hash": stored_hash,
                "calculated_hash": calculated_hash,
                "authoritative_key_used": bool(self.public_key_pem)
            }
        except ValueError:
            return False, "signature_invalid", {"stored_hash": stored_hash}
        except Exception as exc:
            return False, f"signature_error: {exc}", {"stored_hash": stored_hash}

    def verify_hash_signature(
        self,
        hash_str: str,
        signature_b64: str,
        public_key_pem: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Verify standalone hash signature using authoritative public key."""
        clean_hash = hash_str.strip().lower()
        key_to_use_pem = self.public_key_pem or public_key_pem
        if not key_to_use_pem:
            return False, "missing_public_key"

        try:
            public_key = ECC.import_key(key_to_use_pem)
            signature_bytes = base64.b64decode(signature_b64)
            hash_obj = SHA256.new(clean_hash.encode('utf-8'))
            verifier = DSS.new(public_key, 'fips-186-3')
            verifier.verify(hash_obj, signature_bytes)
            return True, "ok"
        except ValueError:
            return False, "signature_invalid"
        except Exception as exc:
            return False, f"signature_error: {exc}"


crypto_service = CryptoService()
