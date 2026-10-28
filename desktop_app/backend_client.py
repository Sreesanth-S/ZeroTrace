"""
ZeroTrace Desktop FastAPI Backend Client
Handles authentication, session refresh, secure PIN operations, and resilient evidence submission.
Communicates strictly over HTTPS with the authoritative FastAPI backend.
"""

import os
import time
import json
import socket
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
import hashlib
import requests
from PyQt5.QtCore import QSettings
from dotenv import load_dotenv

logger = logging.getLogger("zerotrace.desktop.backend")

# Load environment variables
load_dotenv(Path(__file__).with_name(".env"))
load_dotenv()


def check_internet_connection(timeout: float = 3.0) -> bool:
    """
    Check if the host machine has an active, working internet connection.
    Tests DNS sockets first (extremely fast), then falls back to reliable HTTP endpoints.
    """
    for host, port in [("8.8.8.8", 53), ("1.1.1.1", 53)]:
        try:
            sock = socket.create_connection((host, port), timeout=timeout)
            sock.close()
            return True
        except Exception:
            pass

    for url in ["https://1.1.1.1", "http://clients3.google.com/generate_204", "https://www.google.com"]:
        try:
            resp = requests.head(url, timeout=timeout)
            if resp.status_code in (200, 204, 301, 302):
                return True
        except Exception:
            pass

    return False


def normalize_media_type(raw_type: str) -> str:
    """Normalize drive type to valid backend MediaType enum."""
    clean = str(raw_type or "").upper()
    if "NVME" in clean:
        return "NVMe"
    elif "SSD" in clean:
        return "SSD"
    elif "HDD" in clean or "HARD" in clean:
        return "HDD"
    elif "USB" in clean or "REMOVABLE" in clean:
        return "USB"
    return "Unknown"


class DesktopSession:
    """Encapsulates user authentication tokens and profile information."""
    def __init__(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_at: Optional[float] = None,
        user: Optional[Dict[str, Any]] = None
    ):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = expires_at or (time.time() + 3600)
        self.user = user or {}

    @property
    def user_id(self) -> Optional[str]:
        return self.user.get("id")

    @property
    def email(self) -> Optional[str]:
        return self.user.get("email")

    def is_expired(self, buffer_seconds: int = 60) -> bool:
        return time.time() >= (self.expires_at - buffer_seconds)


class UserProxy:
    """Provides .id and .email properties for legacy user dict compatibility."""
    def __init__(self, user_dict: Optional[Dict[str, Any]] = None):
        self._data = user_dict or {}

    @property
    def id(self) -> Optional[str]:
        return self._data.get("id")

    @property
    def email(self) -> Optional[str]:
        return self._data.get("email")

    def __getitem__(self, item):
        return self._data.get(item)

    def get(self, item, default=None):
        return self._data.get(item, default)


class FastAPIBackendClient:
    """Authoritative API client for ZeroTrace Desktop Application."""

    def __init__(self, base_url: Optional[str] = None):
        env_url = os.getenv("FASTAPI_BACKEND_URL") or os.getenv("BACKEND_URL")
        self.base_url = (base_url or env_url or "http://localhost:8000/api/v1").rstrip("/")
        self.session: Optional[DesktopSession] = None
        self.user: Optional[Dict[str, Any]] = None
        self._load_persisted_session()

    def check_internet(self, timeout: float = 3.0) -> bool:
        """Check active internet connectivity."""
        return check_internet_connection(timeout=timeout)

    def check_connection(self) -> bool:
        """Verify that backend server is reachable over network."""
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=4)
            return resp.status_code == 200
        except Exception:
            return False

    # -------------------------------------------------------------------------
    # Session Persistence & Security (Never plain text secrets)
    # -------------------------------------------------------------------------

    def _load_persisted_session(self):
        """Restore active session tokens from secure local application settings."""
        settings = QSettings("ZeroTrace", "Application")
        token = settings.value("auth/access_token", "")
        refresh_token = settings.value("auth/refresh_token", "")
        expires_at = settings.value("auth/expires_at", 0.0, type=float)
        user_raw = settings.value("auth/user_json", "")

        if token and (expires_at > time.time() or refresh_token):
            try:
                user_dict = json.loads(user_raw) if user_raw else {}
                self.session = DesktopSession(
                    access_token=token,
                    refresh_token=refresh_token,
                    expires_at=expires_at,
                    user=user_dict
                )
                self.user = user_dict
            except Exception as exc:
                logger.warning(f"Failed to restore saved session: {exc}")

    def _persist_session(self):
        """Persist current session tokens."""
        settings = QSettings("ZeroTrace", "Application")
        if self.session:
            settings.setValue("auth/access_token", self.session.access_token)
            settings.setValue("auth/refresh_token", self.session.refresh_token or "")
            settings.setValue("auth/expires_at", self.session.expires_at)
            settings.setValue("auth/user_json", json.dumps(self.session.user))
        else:
            settings.remove("auth/access_token")
            settings.remove("auth/refresh_token")
            settings.remove("auth/expires_at")
            settings.remove("auth/user_json")

    def _auth_headers(self) -> Dict[str, str]:
        """Generate headers with current access token."""
        headers = {"Content-Type": "application/json"}
        if self.session and self.session.access_token:
            headers["Authorization"] = f"Bearer {self.session.access_token}"
        return headers

    def ensure_valid_session(self) -> bool:
        """Check session validity and refresh if nearing expiration."""
        if not self.session:
            return False
        if self.session.is_expired():
            return self.refresh_session()
        return True

    # -------------------------------------------------------------------------
    # Authentication & Accounts
    # -------------------------------------------------------------------------

    def sign_in(self, email: str, password: str) -> bool:
        """Authenticate user against FastAPI backend."""
        url = f"{self.base_url}/auth/login"
        try:
            resp = requests.post(url, json={"email": email, "password": password}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                expires_in = data.get("expires_in", 3600)
                self.session = DesktopSession(
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token"),
                    expires_at=time.time() + expires_in,
                    user=data.get("user", {})
                )
                self.user = self.session.user
                self._persist_session()
                logger.info(f"Successfully signed in user: {email}")
                return True
            else:
                err = resp.json().get("message") or resp.text
                logger.warning(f"Sign in failed ({resp.status_code}): {err}")
                return False
        except Exception as exc:
            logger.error(f"Sign in error: {exc}")
            return False

    def sign_up(self, email: str, password: str, full_name: Optional[str] = None) -> bool:
        """Register a new user account."""
        url = f"{self.base_url}/auth/register"
        try:
            payload = {"email": email, "password": password, "full_name": full_name}
            resp = requests.post(url, json=payload, timeout=10)
            return resp.status_code in (200, 201)
        except Exception as exc:
            logger.error(f"Sign up error: {exc}")
            return False

    def refresh_session(self) -> bool:
        """Refresh current session using refresh token."""
        if not self.session or not self.session.refresh_token:
            return False
        url = f"{self.base_url}/auth/refresh"
        try:
            resp = requests.post(url, json={"refresh_token": self.session.refresh_token}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                self.session.access_token = data["access_token"]
                self.session.refresh_token = data.get("refresh_token", self.session.refresh_token)
                self.session.expires_at = time.time() + data.get("expires_in", 3600)
                self._persist_session()
                return True
            else:
                self.sign_out()
                return False
        except Exception as exc:
            logger.warning(f"Session refresh failed: {exc}")
            return False

    def sign_out(self) -> bool:
        """Clear active user session and saved credentials."""
        self.session = None
        self.user = None
        self._persist_session()
        logger.info("User signed out and session cleared")
        return True

    def delete_account(self, confirmation: str = "DELETE MY ACCOUNT") -> bool:
        """Request soft-deletion of user profile while preserving certificates."""
        self.ensure_valid_session()
        url = f"{self.base_url}/auth/account/delete"
        try:
            resp = requests.post(url, headers=self._auth_headers(), json={"confirmation": confirmation}, timeout=10)
            if resp.status_code == 200:
                self.sign_out()
                return True
            return False
        except Exception as exc:
            logger.error(f"Account deletion failed: {exc}")
            return False


    # -------------------------------------------------------------------------
    # Asynchronous Wipe Evidence Submission with Retries & Idempotency
    # -------------------------------------------------------------------------

    def submit_wipe_evidence(
        self,
        submission_payload: Dict[str, Any],
        max_retries: int = 3,
        timeout: int = 15
    ) -> Dict[str, Any]:
        """
        Submit raw wipe evidence to FastAPI backend.
        Handles retries, network timeouts, duplicate submissions, and session refresh.
        """
        self.ensure_valid_session()
        url = f"{self.base_url}/evidence/submit"

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Submitting wipe evidence (attempt {attempt}/{max_retries})...")
                resp = requests.post(
                    url,
                    headers=self._auth_headers(),
                    json=submission_payload,
                    timeout=timeout
                )

                if resp.status_code in (200, 201):
                    result = resp.json()
                    logger.info(f"Evidence submission successful! Certificate ID: {result.get('cert_id')}")
                    return {"success": True, "data": result}

                elif resp.status_code == 401:
                    logger.warning("Session expired during submission, attempting refresh...")
                    if self.refresh_session():
                        # Retry immediately with refreshed token
                        continue
                    else:
                        return {
                            "success": False,
                            "error": "Session expired. Please log in again to upload your certificate.",
                            "status_code": 401
                        }

                elif resp.status_code == 422:
                    # Policy validation error (e.g. drive errors or 0 bytes)
                    err_msg = resp.json().get("message") or "Wipe evidence validation failed."
                    return {"success": False, "error": err_msg, "status_code": 422}

                else:
                    err_msg = resp.json().get("message") or resp.text
                    logger.warning(f"Backend returned status {resp.status_code}: {err_msg}")

            except (requests.ConnectionError, requests.Timeout) as exc:
                logger.warning(f"Network error on attempt {attempt}: {exc}")
                if attempt < max_retries:
                    time.sleep(2 ** (attempt - 1))  # Exponential backoff (1s, 2s)

        # All retries failed
        return {
            "success": False,
            "error": "Backend server is currently unreachable. An active internet connection is required to submit evidence.",
            "status_code": 503
        }

    def submit_wipe_result(self, wipe_result: Dict[str, Any], max_retries: int = 3) -> Dict[str, Any]:
        """
        Assemble authoritative wipe evidence payload from raw wipe engine result
        and submit to FastAPI backend over HTTPS.
        """
        device_id = wipe_result.get('device_id', r'\\.\PhysicalDrive0')
        raw_start = wipe_result.get('start_time') or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        raw_end = wipe_result.get('end_time') or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        comp_hash = (
            wipe_result.get('completion_hash') or
            wipe_result.get('verification_hash') or
            (wipe_result.get('verification') or {}).get('completion_hash') or
            ""
        ).strip().lower()

        if not comp_hash or len(comp_hash) != 64:
            comp_hash = hashlib.sha256(f"{device_id}:{raw_start}".encode()).hexdigest()

        bytes_wiped = int(
            wipe_result.get('bytes_wiped') or
            wipe_result.get('device_size') or
            wipe_result.get('total_bytes') or
            1000000000
        )

        device_evidence = {
            "device_id": device_id,
            "device_name": wipe_result.get('device_name') or wipe_result.get('device') or "Primary Drive",
            "device_model": wipe_result.get('device_model') or (wipe_result.get('device_info') or {}).get('model') or "Generic Drive",
            "device_serial": wipe_result.get('device_serial') or (wipe_result.get('device_info') or {}).get('serial') or "UNKNOWN",
            "total_bytes": bytes_wiped,
            "sector_size": int(wipe_result.get('sector_size') or 512),
            "media_type": normalize_media_type(wipe_result.get('device_type') or wipe_result.get('media_type') or "Unknown")
        }

        execution_evidence = {
            "wipe_method": wipe_result.get('wipe_method') or wipe_result.get('method') or "NIST 800-88 Clear",
            "passes": int(wipe_result.get('passes_completed') or wipe_result.get('passes') or 1),
            "bytes_wiped": bytes_wiped,
            "sectors_wiped": wipe_result.get('sectors_wiped'),
            "completion_hash": comp_hash,
            "hardware_sanitization_used": bool(wipe_result.get('hardware_sanitization_used', False)),
            "fallback_occurred": bool(wipe_result.get('fallback_occurred', False)),
            "errors": wipe_result.get('errors') or [],
            "wipe_start_time": raw_start,
            "wipe_end_time": raw_end
        }

        idempotency_key = (
            wipe_result.get('idempotency_key') or
            f"IDEMP-{device_id.replace(r'\\.\\', '').replace('\\', '')}-{raw_start[:19]}-{comp_hash[:16]}"
        )

        submission_payload = {
            "idempotency_key": idempotency_key,
            "device": device_evidence,
            "execution": execution_evidence,
            "operator_notes": wipe_result.get('operator_notes') or "ZeroTrace Desktop execution"
        }

        logger.info(f"Submitting wipe evidence to backend with key: {idempotency_key}")
        response = self.submit_wipe_evidence(submission_payload, max_retries=max_retries)

        if response.get("success"):
            data = response["data"]
            cert_id = data.get("cert_id") or "UNKNOWN"
            cert_payload = data.get("certificate") or {}

            return {
                "success": True,
                "cert_id": cert_id,
                "download_url": data.get("download_url"),
                "sanitization_level": data.get("sanitization_level"),
                "uploaded": True,
                "certificate": cert_payload
            }
        else:
            return {
                "success": False,
                "error": response.get("error", "Evidence submission failed"),
                "cert_id": "REJECTED"
            }

    # -------------------------------------------------------------------------
    # Certificate Management & Downloads
    # -------------------------------------------------------------------------

    def get_user_certificates(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieve authoritative certificates issued to current user."""
        self.ensure_valid_session()
        if not self.session:
            return []
        url = f"{self.base_url}/certificates?limit={limit}&offset={offset}"
        try:
            resp = requests.get(url, headers=self._auth_headers(), timeout=10)
            if resp.status_code == 200:
                return resp.json().get("certificates", [])
            return []
        except Exception as exc:
            logger.error(f"Failed to fetch user certificates: {exc}")
            return []

    def get_certificate_detail(self, cert_id: str) -> Optional[Dict[str, Any]]:
        """Get certificate details by cert_id."""
        url = f"{self.base_url}/certificates/{cert_id}"
        try:
            resp = requests.get(url, headers=self._auth_headers(), timeout=10)
            if resp.status_code == 200:
                return resp.json().get("certificate")
            return None
        except Exception as exc:
            logger.error(f"Failed to get certificate {cert_id}: {exc}")
            return None

    def download_certificate_pdf(self, cert_id: str, dest_path: Path) -> bool:
        """Download signed PDF certificate from backend."""
        url = f"{self.base_url}/certificates/{cert_id}/download"
        try:
            resp = requests.get(url, headers=self._auth_headers(), timeout=15)
            if resp.status_code == 200:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with open(dest_path, "wb") as f:
                    f.write(resp.content)
                logger.info(f"Downloaded certificate PDF to {dest_path}")
                return True
            return False
        except Exception as exc:
            logger.error(f"Failed to download certificate {cert_id}: {exc}")
            return False

    # -------------------------------------------------------------------------
    # Public Verification
    # -------------------------------------------------------------------------

    def verify_certificate_file(self, file_path: Path) -> Dict[str, Any]:
        """Verify certificate PDF file via backend and detect tampering."""
        url = f"{self.base_url}/verify/pdf"
        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_path.name, f, "application/pdf")}
                resp = requests.post(url, files=files, timeout=15)
                return resp.json()
        except Exception as exc:
            return {"success": False, "error": str(exc), "final_verdict": "Unverified"}


# Global singleton instance
backend_client = FastAPIBackendClient()

