"""
Certificate Management Endpoints
Handles listing, details, PDF and JSON downloads, and auditable revocation of issued certificates.
"""

from fastapi import APIRouter, Depends, Request, Response, Query, status
from typing import Dict, Any, List, Optional
import httpx
import json

from backend.app.schemas.certificate import RevocationRequest, RevocationResponse
from backend.app.core.security import get_current_user, get_optional_user
from backend.app.core.errors import NotFoundError, ForbiddenError
from backend.app.services.supabase_service import supabase_service
from backend.app.services.pdf_service import pdf_service

router = APIRouter(prefix="/certificates", tags=["Certificates"])


@router.get("", status_code=status.HTTP_200_OK)
async def list_certificates(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """List all certificates issued to the authenticated user."""
    user_id = user["id"]
    certs = await supabase_service.list_certificates_for_user(user_id=user_id, limit=limit, offset=offset)
    return {
        "success": True,
        "count": len(certs),
        "limit": limit,
        "offset": offset,
        "certificates": certs
    }


@router.get("/{cert_id}", status_code=status.HTTP_200_OK)
async def get_certificate(
    cert_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """Retrieve details of an authoritative certificate."""
    cert = await supabase_service.get_certificate_by_cert_id(cert_id)
    if not cert:
        raise NotFoundError(f"Certificate {cert_id} not found")

    return {
        "success": True,
        "certificate": cert
    }


@router.get("/{cert_id}/download")
async def download_certificate_pdf(cert_id: str):
    """Stream or download the signed certificate PDF from private storage."""
    cert = await supabase_service.get_certificate_by_cert_id(cert_id)
    if not cert:
        raise NotFoundError(f"Certificate {cert_id} not found")

    user_id = cert.get("user_id") or "anonymous"
    stored_bytes = supabase_service.get_stored_pdf(user_id, cert_id)
    if stored_bytes:
        return Response(
            content=stored_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{cert_id}.pdf"'}
        )

    pdf_url = cert.get("pdf_url")
    if pdf_url:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(pdf_url)
                if resp.status_code == 200:
                    return Response(
                        content=resp.content,
                        media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{cert_id}.pdf"'}
                    )
        except Exception:
            pass

    # Fallback: Regenerate PDF on the fly from certificate record
    pdf_bytes = pdf_service.generate_pdf(cert)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{cert_id}.pdf"'}
    )


@router.post("/{cert_id}/revoke", response_model=RevocationResponse)
async def revoke_certificate(
    cert_id: str,
    body: RevocationRequest,
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Revoke an issued certificate with an auditable reason and caller metadata."""
    user_id = user["id"]
    client_ip = request.client.host if request.client else "127.0.0.1"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    user_agent = request.headers.get("user-agent", "unknown")

    result = await supabase_service.revoke_certificate(
        cert_id=cert_id,
        revoked_by=user_id,
        reason=body.reason,
        ip_address=client_ip,
        user_agent=user_agent
    )
    return result
