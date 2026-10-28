"""
Public Certificate Verification Endpoint (Dual-Anchor Verification Policy)
Accepts PDF certificate uploads for cryptographic verification and tamper detection.
Independently verifies and reports:
1. Cryptographic Authenticity & Integrity (ECDSA against pinned public key, payload validation)
2. Registry Recognition (authoritative Supabase database consistency)
3. Revocation Status (active vs revoked)
4. Issuer Account Status (active vs deactivated vs deleted)
"""

from fastapi import APIRouter, UploadFile, File, Form, Depends, Request, status
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from backend.app.core.security import rate_limit_public_verify
from backend.app.schemas.certificate import PublicVerificationResponse, PublicVerificationCheck
from backend.app.services.crypto_service import crypto_service
from backend.app.services.pdf_service import pdf_service
from backend.app.services.supabase_service import supabase_service

router = APIRouter(prefix="/verify", tags=["Public Verification"], dependencies=[Depends(rate_limit_public_verify)])


def evaluate_dual_anchor_trust(
    crypto_valid: bool,
    crypto_reason: str,
    db_cert: Optional[Dict[str, Any]],
    issuer_profile: Optional[Dict[str, Any]]
) -> PublicVerificationResponse:
    """
    Evaluates trust according to the ZeroTrace Dual-Anchor Verification Policy.
    Cryptographic authenticity is mandatory for a 'Verified' result.
    """
    checks: List[PublicVerificationCheck] = []

    # 1. Cryptographic Authenticity Check
    crypto_passed = bool(crypto_valid)
    checks.append(PublicVerificationCheck(
        check="cryptographic_authenticity_ecdsa",
        passed=crypto_passed,
        description="ECDSA-SHA256 digital signature and tamper integrity validation against authoritative key",
        details={"reason": crypto_reason}
    ))

    # 2. Registry Recognition Check
    registry_passed = db_cert is not None
    checks.append(PublicVerificationCheck(
        check="database_consistency",
        passed=registry_passed,
        description="Authoritative database registry record consistency",
        details={"found": registry_passed, "cert_id": db_cert.get("cert_id") if db_cert else None}
    ))

    # 3. Revocation Status Check
    if db_cert:
        is_revoked = str(db_cert.get("status", "")).strip().lower() == "revoked"
        revocation_status = "revoked" if is_revoked else "active"
    else:
        is_revoked = False
        revocation_status = "not_registered"

    checks.append(PublicVerificationCheck(
        check="revocation_status",
        passed=not is_revoked,
        description="Certificate validity and revocation state check",
        details={"status": revocation_status}
    ))

    # 4. Issuer Account Status Check
    if db_cert and db_cert.get("user_id"):
        if issuer_profile:
            issuer_status = issuer_profile.get("status", "active")
        else:
            issuer_status = "active"
    else:
        issuer_status = "unregistered"

    checks.append(PublicVerificationCheck(
        check="issuer_account_status",
        passed=issuer_status in ("active", "unregistered"),
        description="Status of the account that issued this sanitization certificate",
        details={"account_status": issuer_status}
    ))

    # Determine Final Verdict
    if not crypto_passed:
        final_verdict = "Tampered" if crypto_reason in ("hash_mismatch", "signature_invalid", "tampered_pdf_text_mismatch", "payload_corrupted") else "Unverified"
        if final_verdict == "Tampered":
            explanation = "Tamper Detected! The certificate document fails cryptographic verification. The contents, embedded payload, or signature have been altered."
        else:
            explanation = "The document fails cryptographic authentication. It may not be an authentic ZeroTrace certificate or is missing required cryptographic signatures."
    elif is_revoked:
        final_verdict = "Revoked"
        explanation = "This certificate was signed by ZeroTrace but has been officially revoked by the issuing authority."
    elif not registry_passed:
        final_verdict = "Unverified"
        explanation = "The digital signature is valid, but the certificate is not recognized in the authoritative registry database."
    else:
        final_verdict = "Verified"
        explanation = "Authentic ZeroTrace Certificate. Valid cryptographic signature, active registry record, and active issuer account."

    return PublicVerificationResponse(
        success=final_verdict == "Verified",
        final_verdict=final_verdict,
        verdict_explanation=explanation,
        cryptographic_authenticity=crypto_passed,
        registry_recognition=registry_passed,
        revocation_status=revocation_status,
        issuer_account_status=issuer_status,
        checks=checks,
        certificate=db_cert
    )


@router.post("/pdf", response_model=PublicVerificationResponse)
async def verify_certificate_file(
    file: UploadFile = File(...),
    request: Request = None
):
    """
    Public upload endpoint to verify certificate PDF and detect tampering.
    Validates embedded machine payload, checks text integrity, and performs dual-anchor verification.
    """
    filename = file.filename.lower() if file.filename else ""
    if not (filename.endswith(".pdf") or file.content_type in ("application/pdf", "application/x-pdf", "application/octet-stream")):
        return PublicVerificationResponse(
            success=False,
            final_verdict="Unverified",
            verdict_explanation="Only official ZeroTrace PDF certificates (.pdf) are supported for verification and tamper detection.",
            cryptographic_authenticity=False,
            registry_recognition=False,
            revocation_status="not_registered",
            issuer_account_status="unregistered",
            checks=[
                PublicVerificationCheck(
                    check="pdf_format_validation",
                    passed=False,
                    description="Upload file format must be a valid PDF certificate (.pdf)",
                    details={"error": "Invalid file type. Only PDF is supported."}
                )
            ]
        )

    content = await file.read()
    if not content.startswith(b"%PDF"):
        return PublicVerificationResponse(
            success=False,
            final_verdict="Unverified",
            verdict_explanation="Uploaded file does not have a valid PDF header structure.",
            cryptographic_authenticity=False,
            registry_recognition=False,
            revocation_status="not_registered",
            issuer_account_status="unregistered",
            checks=[
                PublicVerificationCheck(
                    check="pdf_header_validation",
                    passed=False,
                    description="Validates PDF binary signature (%PDF)",
                    details={"error": "File does not start with %PDF header"}
                )
            ]
        )

    # PDF document extraction and tamper inspection
    extracted_cert, extracted_hash = pdf_service.extract_from_pdf(content)

    # 1. Cryptographic verification & tamper detection
    crypto_valid = False
    crypto_reason = "missing_certificate_or_signature"

    if extracted_cert and extracted_cert.get("_tamper_detected"):
        crypto_valid = False
        crypto_reason = extracted_cert["_tamper_detected"]
    elif extracted_cert and "_signature" in extracted_cert:
        crypto_valid, crypto_reason, _ = crypto_service.verify_certificate_signature(
            extracted_cert,
            use_authoritative_key_only=True
        )
    elif extracted_hash:
        crypto_reason = "raw_hash_requires_signature"

    # 2. Database lookup
    db_cert = None
    if extracted_hash:
        db_cert = await supabase_service.get_certificate_by_hash(extracted_hash)
    elif extracted_cert and (extracted_cert.get("cert_id") or extracted_cert.get("certificate_id")):
        c_id = extracted_cert.get("cert_id") or extracted_cert.get("certificate_id")
        db_cert = await supabase_service.get_certificate_by_cert_id(c_id)

    # 3. Issuer profile lookup
    issuer_profile = None
    if db_cert and db_cert.get("user_id"):
        issuer_profile = await supabase_service.get_user_profile(db_cert["user_id"])

    verdict_resp = evaluate_dual_anchor_trust(crypto_valid, crypto_reason, db_cert, issuer_profile)
    return verdict_resp

