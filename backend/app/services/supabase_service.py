"""
Authoritative Supabase Storage and Database Service
Privileged database writes and bucket uploads using the Supabase Service Key.
Supports private Supabase Storage for PDFs and signed JSON.
Core tables: ONLY `certificates` and `user_profiles`.
Includes built-in in-memory mock isolation when running in testing mode.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import httpx
import logging
import json

from backend.app.core.config import settings
from backend.app.core.errors import NotFoundError, ConflictError

logger = logging.getLogger(__name__)


class SupabaseService:
    def __init__(self):
        self.base_url = settings.SUPABASE_URL.rstrip('/')
        self.rest_url = f"{self.base_url}/rest/v1"
        self.storage_url = f"{self.base_url}/storage/v1"
        self.headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

        # In-memory test store used when ENVIRONMENT == 'testing'
        self._test_certificates: Dict[str, Any] = {}
        self._test_profiles: Dict[str, Any] = {}
        self._test_storage: Dict[str, bytes] = {}

    def reset_test_store(self):
        """Reset in-memory storage for fresh test runs."""
        self._test_certificates.clear()
        self._test_profiles.clear()
        self._test_storage.clear()

    async def get_idempotent_submission(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        """Look up existing certificate directly from certificates table by idempotency key."""
        if not idempotency_key:
            return None

        if settings.ENVIRONMENT == "testing":
            for c in self._test_certificates.values():
                if c.get("idempotency_key") == idempotency_key:
                    return c
            return None

        url = f"{self.rest_url}/certificates?idempotency_key=eq.{idempotency_key}&select=*"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=self.headers)
                if resp.status_code == 200:
                    rows = resp.json()
                    return rows[0] if rows else None
        except Exception as exc:
            logger.warning(f"Could not query certificates by idempotency_key: {exc}")
        return None

    async def insert_certificate(self, cert_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insert authoritative certificate record into PostgreSQL certificates table.
        Backend is the sole authority for certificate creation and signature persistence.
        """
        if settings.ENVIRONMENT == "testing":
            cid = cert_data.get("cert_id")
            if cid in self._test_certificates:
                raise ConflictError(f"Certificate with cert_id '{cid}' already exists.")
            idemp = cert_data.get("idempotency_key")
            if idemp:
                for c in self._test_certificates.values():
                    if c.get("idempotency_key") == idemp:
                        raise ConflictError(f"Certificate with idempotency key '{idemp}' already exists.")
            self._test_certificates[cid] = cert_data
            return cert_data

        url = f"{self.rest_url}/certificates"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, headers=self.headers, json=cert_data)
                if resp.status_code in (200, 201):
                    rows = resp.json()
                    return rows[0] if rows else cert_data
                elif resp.status_code == 409:
                    raise ConflictError(f"Certificate with cert_id '{cert_data.get('cert_id')}' already exists.")
                else:
                    raise Exception(f"Supabase returned status {resp.status_code}: {resp.text}")
        except ConflictError:
            raise
        except Exception as exc:
            logger.error(f"Failed to insert certificate: {exc}")
            raise

    async def get_certificate_by_cert_id(self, cert_id: str) -> Optional[Dict[str, Any]]:
        """Fetch certificate by public cert_id."""
        if settings.ENVIRONMENT == "testing":
            return self._test_certificates.get(cert_id)

        url = f"{self.rest_url}/certificates?cert_id=eq.{cert_id}&select=*"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=self.headers)
                if resp.status_code == 200:
                    rows = resp.json()
                    return rows[0] if rows else None
        except Exception as exc:
            logger.error(f"Error fetching certificate by cert_id: {exc}")
        return None

    async def get_certificate_by_hash(self, verification_hash: str) -> Optional[Dict[str, Any]]:
        """Fetch certificate by verification hash."""
        clean_hash = verification_hash.strip().lower()
        if settings.ENVIRONMENT == "testing":
            for c in self._test_certificates.values():
                chash = (c.get("verification_hash") or "").strip().lower()
                if chash == clean_hash:
                    return c
            return None

        url = f"{self.rest_url}/certificates?verification_hash=ilike.{clean_hash}&select=*"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=self.headers)
                if resp.status_code == 200:
                    rows = resp.json()
                    return rows[0] if rows else None
        except Exception as exc:
            logger.error(f"Error fetching certificate by hash: {exc}")
        return None

    async def list_certificates_for_user(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List certificates owned by user with pagination."""
        if settings.ENVIRONMENT == "testing":
            matching = [c for c in self._test_certificates.values() if c.get("user_id") == user_id]
            return matching[offset:offset + limit]

        url = f"{self.rest_url}/certificates?user_id=eq.{user_id}&order=created_at.desc&limit={limit}&offset={offset}&select=*"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=self.headers)
                if resp.status_code == 200:
                    return resp.json()
        except Exception as exc:
            logger.error(f"Error listing user certificates: {exc}")
        return []

    async def revoke_certificate(
        self,
        cert_id: str,
        revoked_by: Optional[str],
        reason: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Revoke a certificate by directly updating its revocation fields in the certificates table.
        Sole backend authority ensures untampered auditability without auxiliary logging tables.
        """
        cert = await self.get_certificate_by_cert_id(cert_id)
        if not cert:
            raise NotFoundError(f"Certificate {cert_id} not found")

        if cert.get("status") == "Revoked" or cert.get("validation_status") == "Revoked":
            raise ConflictError(f"Certificate {cert_id} is already revoked")

        if revoked_by and cert.get("user_id") and cert.get("user_id") != revoked_by:
            raise ConflictError("You do not have permission to revoke this certificate")

        now_iso = datetime.now(timezone.utc).isoformat()

        if settings.ENVIRONMENT == "testing":
            c = self._test_certificates[cert_id]
            c["status"] = "Revoked"
            c["validation_status"] = "Revoked"
            c["revoked_at"] = now_iso
            c["revoked_by"] = revoked_by
            c["revocation_reason"] = reason
            c["revocation_ip"] = ip_address
            c["revocation_user_agent"] = user_agent
            return {
                "success": True,
                "cert_id": cert_id,
                "status": "Revoked",
                "validation_status": "Revoked",
                "revoked_at": now_iso,
                "reason": reason,
                "revoked_by": revoked_by
            }

        update_url = f"{self.rest_url}/certificates?cert_id=eq.{cert_id}"
        patch_payload = {
            "status": "Revoked",
            "validation_status": "Revoked",
            "revoked_at": now_iso,
            "revoked_by": revoked_by,
            "revocation_reason": reason,
            "revocation_ip": ip_address,
            "revocation_user_agent": user_agent,
            "updated_at": now_iso
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.patch(update_url, headers=self.headers, json=patch_payload)
            if resp.status_code not in (200, 204):
                raise Exception(f"Failed to update certificate status: {resp.text}")

        return {
            "success": True,
            "cert_id": cert_id,
            "status": "Revoked",
            "validation_status": "Revoked",
            "revoked_at": now_iso,
            "reason": reason,
            "revoked_by": revoked_by
        }

    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Fetch user profile including active/deactivated status."""
        if settings.ENVIRONMENT == "testing":
            return self._test_profiles.get(user_id, {"id": user_id, "status": "active"})

        url = f"{self.rest_url}/user_profiles?id=eq.{user_id}&select=*"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=self.headers)
                if resp.status_code == 200:
                    rows = resp.json()
                    return rows[0] if rows else None
        except Exception as exc:
            logger.error(f"Error fetching user profile: {exc}")
        return None

    async def update_user_status(self, user_id: str, new_status: str) -> Dict[str, Any]:
        """Update account status (e.g. active, deactivated, deleted) without deleting historical certs."""
        if settings.ENVIRONMENT == "testing":
            self._test_profiles.setdefault(user_id, {})["status"] = new_status
            return {"success": True, "user_id": user_id, "status": new_status}

        url = f"{self.rest_url}/user_profiles?id=eq.{user_id}"
        payload = {
            "status": new_status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        if new_status in ("deactivated", "deleted"):
            payload["deactivated_at"] = datetime.now(timezone.utc).isoformat()

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.patch(url, headers=self.headers, json=payload)
            if resp.status_code not in (200, 204):
                raise Exception(f"Failed to update user profile status: {resp.text}")
        return {"success": True, "user_id": user_id, "status": new_status}

    async def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update user profile fields (e.g. full_name, organization, phone)."""
        if settings.ENVIRONMENT == "testing":
            profile = self._test_profiles.setdefault(user_id, {"id": user_id, "status": "active"})
            profile.update(updates)
            return {"success": True, "user_id": user_id, "profile": profile}

        url = f"{self.rest_url}/user_profiles?id=eq.{user_id}"
        payload = {**updates, "updated_at": datetime.now(timezone.utc).isoformat()}

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.patch(url, headers=self.headers, json=payload)
            if resp.status_code not in (200, 204):
                upsert_url = f"{self.rest_url}/user_profiles"
                upsert_headers = {**self.headers, "Prefer": "resolution=merge-duplicates"}
                resp2 = await client.post(upsert_url, headers=upsert_headers, json={"id": user_id, **payload})
                if resp2.status_code not in (200, 201, 204):
                    logger.warning(f"Could not update user_profiles table: {resp2.text}")
        return {"success": True, "user_id": user_id, "updates": updates}

    async def upload_certificate_pdf(self, user_id: str, cert_id: str, pdf_bytes: bytes) -> str:
        """
        Upload generated signed PDF to private Supabase Storage bucket ('certificates').
        Sole backend authority writes files using service_role key.
        """
        bucket = settings.SUPABASE_STORAGE_BUCKET
        file_path = f"{user_id}/{cert_id}.pdf"
        storage_ref = f"{self.storage_url}/object/authenticated/{bucket}/{file_path}"

        if settings.ENVIRONMENT == "testing":
            self._test_storage[file_path] = pdf_bytes
            return storage_ref

        upload_url = f"{self.storage_url}/object/{bucket}/{file_path}"
        storage_headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/pdf",
            "x-upsert": "true"
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(upload_url, headers=storage_headers, content=pdf_bytes)
                if resp.status_code in (200, 201):
                    return storage_ref
                else:
                    logger.warning(f"Storage PDF upload returned {resp.status_code}: {resp.text}")
        except Exception as exc:
            logger.warning(f"Failed to upload PDF to Supabase Storage: {exc}")

        return storage_ref

    def get_stored_pdf(self, user_id: str, cert_id: str) -> Optional[bytes]:
        """Retrieve stored PDF bytes from test memory if in testing environment."""
        if settings.ENVIRONMENT == "testing":
            file_path = f"{user_id}/{cert_id}.pdf"
            return self._test_storage.get(file_path)
        return None

    async def auth_sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """Sign in user via Supabase Auth REST endpoint."""
        if settings.ENVIRONMENT == "testing":
            if password == "invalid_password":
                raise Exception("Invalid email or password")
            return {
                "access_token": "mock-test-jwt-token",
                "token_type": "bearer",
                "expires_in": 3600,
                "refresh_token": "mock-test-refresh-token",
                "user": {"id": "11111111-2222-3333-4444-555555555555", "email": email}
            }

        url = f"{self.base_url}/auth/v1/token?grant_type=password"
        headers = {"apikey": settings.SUPABASE_KEY, "Content-Type": "application/json"}
        payload = {"email": email, "password": password}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise Exception(resp.json().get("error_description") or resp.json().get("msg") or "Invalid email or password")
            return resp.json()

    async def auth_sign_up(self, email: str, password: str, full_name: Optional[str] = None) -> Dict[str, Any]:
        """Register new user via Supabase Auth REST endpoint."""
        if settings.ENVIRONMENT == "testing":
            return {
                "access_token": "mock-test-jwt-token",
                "token_type": "bearer",
                "expires_in": 3600,
                "refresh_token": "mock-test-refresh-token",
                "user": {"id": "11111111-2222-3333-4444-555555555555", "email": email, "user_metadata": {"full_name": full_name or ""}}
            }

        url = f"{self.base_url}/auth/v1/signup"
        headers = {"apikey": settings.SUPABASE_KEY, "Content-Type": "application/json"}
        payload = {"email": email, "password": password}
        if full_name:
            payload["data"] = {"full_name": full_name}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code not in (200, 201):
                raise Exception(resp.json().get("error_description") or resp.json().get("msg") or "Registration failed")
            return resp.json()

    async def auth_refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh user session token via Supabase Auth REST endpoint."""
        if settings.ENVIRONMENT == "testing":
            return {
                "access_token": "mock-test-refreshed-jwt-token",
                "token_type": "bearer",
                "expires_in": 3600,
                "refresh_token": refresh_token,
                "user": {"id": "11111111-2222-3333-4444-555555555555", "email": "test-operator@zerotrace.org"}
            }

        url = f"{self.base_url}/auth/v1/token?grant_type=refresh_token"
        headers = {"apikey": settings.SUPABASE_KEY, "Content-Type": "application/json"}
        payload = {"refresh_token": refresh_token}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise Exception("Session expired or refresh token invalid")
            return resp.json()

    async def auth_recover_password(self, email: str) -> Dict[str, Any]:
        """Trigger password recovery email via Supabase Auth REST endpoint."""
        if settings.ENVIRONMENT == "testing":
            return {"success": True, "message": "Password recovery email sent."}

        url = f"{self.base_url}/auth/v1/recover"
        headers = {"apikey": settings.SUPABASE_KEY, "Content-Type": "application/json"}
        payload = {"email": email}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code not in (200, 201):
                err = resp.json().get("error_description") or resp.json().get("msg") or "Failed to send recovery email"
                raise Exception(err)
            return {"success": True, "message": "Password recovery email sent."}

    async def auth_update_password(self, token: str, new_password: str) -> Dict[str, Any]:
        """Update authenticated user password via Supabase Auth REST endpoint."""
        if settings.ENVIRONMENT == "testing":
            return {"success": True, "message": "Password updated successfully."}

        url = f"{self.base_url}/auth/v1/user"
        headers = {
            "apikey": settings.SUPABASE_KEY,
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {"password": new_password}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.put(url, headers=headers, json=payload)
            if resp.status_code not in (200, 201):
                err = resp.json().get("error_description") or resp.json().get("msg") or "Failed to update password"
                raise Exception(err)
            return {"success": True, "message": "Password updated successfully."}


supabase_service = SupabaseService()
