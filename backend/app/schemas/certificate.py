"""
Certificate Schemas and Verification Models
Authoritative contracts for sanitization certificates and audit lifecycle.
"""

from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field


SanitizationLevel = Literal["Purge", "Clear", "Inconclusive/Failed"]
ValidationStatus = Literal["Verified", "Pending", "Revoked", "Inconclusive", "Failed"]
CertificateStatus = Literal["Verified", "Pending", "Revoked"]


class SignatureBlock(BaseModel):
    algorithm: str = "ECDSA-SHA256"
    signature: str
    public_key: str
    signed_at: str
    verification_hash: str
    signing_mode: str = "backend_authoritative"
    signing_key_id: Optional[str] = "zerotrace-authoritative-p256-v1"


class CanonicalCertificateData(BaseModel):
    certificate_id: str
    cert_id: Optional[str] = None
    device_id: str
    device_name: Optional[str] = None
    device_model: Optional[str] = None
    device_serial: Optional[str] = None
    media_type: Optional[str] = "Unknown"
    wipe_method: str
    sanitization_level: SanitizationLevel
    validation_status: ValidationStatus = "Verified"
    validation_summary: Optional[Dict[str, Any]] = None
    policy_version: str = "1.0.0"
    signing_key_id: str = "zerotrace-authoritative-p256-v1"
    bytes_wiped: int
    passes: int
    verification_hash: str
    wipe_start_time: str
    wipe_end_time: str
    issued_at: str
    issuer: str = "ZeroTrace Authoritative Backend"
    compliance: Dict[str, Any]
    _signature: Optional[SignatureBlock] = None


class CertificateRecord(BaseModel):
    id: Optional[str] = None
    cert_id: str
    user_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    device_id: str
    device_name: Optional[str] = None
    device_model: Optional[str] = None
    device_serial: Optional[str] = None
    wipe_method: str
    sanitization_level: str = "Clear"
    validation_status: ValidationStatus = "Verified"
    validation_summary: Optional[Dict[str, Any]] = None
    policy_version: Optional[str] = "1.0.0"
    signing_key_id: Optional[str] = "zerotrace-authoritative-p256-v1"
    verification_hash: str
    pdf_url: Optional[str] = None
    signature: str
    status: CertificateStatus = "Verified"
    revoked_at: Optional[str] = None
    revoked_by: Optional[str] = None
    revocation_reason: Optional[str] = None
    revocation_ip: Optional[str] = None
    revocation_user_agent: Optional[str] = None
    wipe_start_time: Optional[str] = None
    wipe_end_time: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class RevocationRequest(BaseModel):
    reason: str = Field(..., min_length=3, description="Auditable justification for certificate revocation")


class RevocationResponse(BaseModel):
    success: bool
    cert_id: str
    status: str
    validation_status: str = "Revoked"
    revoked_at: str
    reason: str
    revoked_by: Optional[str] = None


class PublicVerificationCheck(BaseModel):
    check: str
    passed: bool
    description: str
    details: Optional[Dict[str, Any]] = None


class PublicVerificationResponse(BaseModel):
    success: bool
    final_verdict: Literal["Verified", "Unverified", "Revoked", "Tampered"]
    verdict_explanation: str
    cryptographic_authenticity: bool
    registry_recognition: bool
    revocation_status: Literal["active", "revoked", "not_registered"]
    issuer_account_status: Literal["active", "deactivated", "deleted", "unregistered"]
    checks: List[PublicVerificationCheck]
    certificate: Optional[Dict[str, Any]] = None
