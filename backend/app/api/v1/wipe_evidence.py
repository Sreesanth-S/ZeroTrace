"""
Wipe Evidence Submission and Authoritative Certificate Issuance Endpoint
Sole authority for validating wipe evidence, signing certificates, and storing records.
Uploads signed PDFs to private Supabase Storage.
"""

from fastapi import APIRouter, Depends, Header, Request, status
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import hashlib

from backend.app.core.config import settings
from backend.app.schemas.evidence import WipeEvidenceSubmission
from backend.app.core.security import get_optional_user
from backend.app.core.errors import EvidenceValidationError
from backend.app.services.evidence_validator import evidence_validator
from backend.app.services.crypto_service import crypto_service
from backend.app.services.pdf_service import pdf_service
from backend.app.services.supabase_service import supabase_service

router = APIRouter(prefix="/evidence", tags=["Wipe Evidence"])


def compute_idempotency_fingerprint(submission: WipeEvidenceSubmission, user_id: Optional[str]) -> str:
    """Generate deterministic fingerprint if client did not supply an idempotency key."""
    raw = (
        f"{user_id or 'anon'}:"
        f"{submission.device.device_id}:"
        f"{submission.execution.wipe_start_time}:"
        f"{submission.execution.completion_hash}"
    )
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


@router.post("/submit", status_code=status.HTTP_201_CREATED)
async def submit_wipe_evidence(
    submission: WipeEvidenceSubmission,
    request: Request,
    user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """
    Submit device wipe evidence from desktop app.
    Validates sanitization outcome, enforces idempotency, generates and signs certificate,
    creates PDF, and persists records in Supabase.
    """
    user_id = user.get("id") if user else None

    # 1. Idempotency Check (queried directly on certificates table)
    idempotency_key = submission.idempotency_key or compute_idempotency_fingerprint(submission, user_id)
    existing_cert = await supabase_service.get_idempotent_submission(idempotency_key)
    if existing_cert and existing_cert.get("cert_id"):
        return {
            "success": True,
            "idempotent_replay": True,
            "message": "Certificate already generated for this wipe execution.",
            "cert_id": existing_cert.get("cert_id"),
            "certificate": existing_cert,
            "sanitization_level": existing_cert.get("sanitization_level", "Clear"),
            "validation_status": existing_cert.get("validation_status", "Verified"),
            "policy_version": existing_cert.get("policy_version", settings.POLICY_VERSION),
            "signing_key_id": existing_cert.get("signing_key_id", settings.SIGNING_KEY_ID),
            "download_url": existing_cert.get("pdf_url")
        }

    # 2. Media-Aware Policy Validation
    sanitization_level, compliance_info = evidence_validator.validate_and_classify(submission)

    # 3. Assemble Canonical Certificate Data
    dev = submission.device
    exec_data = submission.execution
    now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Generate Cert ID: CERT-{sha256(device_id:start_time)[:16]}
    cert_id_seed = f"{dev.device_id}:{exec_data.wipe_start_time}".encode('utf-8')
    cert_id = f"CERT-{hashlib.sha256(cert_id_seed).hexdigest()[:16].upper()}"

    canonical_cert = {
        "certificate_id": cert_id,
        "cert_id": cert_id,
        "device_id": dev.device_id,
        "device_name": dev.device_name or dev.device_model or "Primary Drive",
        "device_model": dev.device_model or "Generic Drive",
        "device_serial": dev.device_serial or "UNKNOWN",
        "media_type": dev.media_type,
        "wipe_method": exec_data.wipe_method,
        "sanitization_level": sanitization_level,
        "validation_status": "Verified",
        "validation_summary": compliance_info,
        "policy_version": settings.POLICY_VERSION,
        "signing_key_id": settings.SIGNING_KEY_ID,
        "bytes_wiped": exec_data.bytes_wiped,
        "passes": exec_data.passes,
        "verification_hash": exec_data.completion_hash,
        "wipe_start_time": exec_data.wipe_start_time,
        "wipe_end_time": exec_data.wipe_end_time,
        "issued_at": now_utc,
        "issuer": "ZeroTrace Authoritative Backend",
        "compliance": compliance_info
    }

    # 4. Cryptographic Signing (Authoritative Server-Side Private Key)
    signed_payload = crypto_service.sign_certificate_payload(canonical_cert)
    signature_block = signed_payload["_signature"]

    # 5. Generate Signed PDF
    pdf_bytes = pdf_service.generate_pdf(signed_payload)

    # 6. Upload PDF to private Supabase Storage
    owner_id = user_id or "anonymous"
    pdf_url = await supabase_service.upload_certificate_pdf(
        user_id=owner_id,
        cert_id=cert_id,
        pdf_bytes=pdf_bytes
    )

    # 7. Persist Certificate to PostgreSQL (Core certificates table)
    db_record = {
        "cert_id": cert_id,
        "user_id": user_id,
        "idempotency_key": idempotency_key,
        "device_id": dev.device_id,
        "device_name": canonical_cert["device_name"],
        "device_model": canonical_cert["device_model"],
        "device_serial": canonical_cert["device_serial"],
        "wipe_method": canonical_cert["wipe_method"],
        "sanitization_level": sanitization_level,
        "validation_status": "Verified",
        "validation_summary": compliance_info,
        "policy_version": settings.POLICY_VERSION,
        "signing_key_id": settings.SIGNING_KEY_ID,
        "verification_hash": canonical_cert["verification_hash"],
        "pdf_url": pdf_url,
        "signature": signature_block["signature"],
        "status": "Verified",
        "wipe_start_time": exec_data.wipe_start_time,
        "wipe_end_time": exec_data.wipe_end_time,
    }

    persisted_cert = await supabase_service.insert_certificate(db_record)

    return {
        "success": True,
        "idempotent_replay": False,
        "cert_id": cert_id,
        "sanitization_level": sanitization_level,
        "validation_status": "Verified",
        "policy_version": settings.POLICY_VERSION,
        "signing_key_id": settings.SIGNING_KEY_ID,
        "verification_hash": canonical_cert["verification_hash"],
        "signature": signature_block["signature"],
        "download_url": pdf_url,
        "certificate": signed_payload
    }
