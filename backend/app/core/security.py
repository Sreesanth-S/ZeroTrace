"""
Security and Authentication Dependencies
Handles Supabase JWT validation, user retrieval, and public rate limiting.
"""

import time
from typing import Optional, Dict, Any
from collections import defaultdict
import httpx
from fastapi import Header, Request, HTTPException, status
from backend.app.core.config import settings
from backend.app.core.errors import UnauthorizedError, ForbiddenError


class RateLimiter:
    """Sliding-window in-memory rate limiter per IP address."""
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.window_seconds = 60
        self.history = defaultdict(list)

    def check(self, ip: str):
        now = time.time()
        window_start = now - self.window_seconds
        # Clean timestamps older than window
        self.history[ip] = [t for t in self.history[ip] if t > window_start]
        if len(self.history[ip]) >= self.requests_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.requests_per_minute} requests per minute."
            )
        self.history[ip].append(now)


public_verify_limiter = RateLimiter(requests_per_minute=30)


async def verify_supabase_token(token: str) -> Dict[str, Any]:
    """Verify Supabase bearer token against Supabase Auth API."""
    if not token:
        raise UnauthorizedError("Missing authentication token")

    clean_token = token.replace("Bearer ", "").strip()
    auth_url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/user"
    headers = {
        "Authorization": f"Bearer {clean_token}",
        "apikey": settings.SUPABASE_KEY
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(auth_url, headers=headers)
            if resp.status_code != 200:
                raise UnauthorizedError("Invalid or expired authentication token")
            return resp.json()
    except httpx.RequestError as exc:
        raise UnauthorizedError(f"Could not reach authentication service: {exc}")


async def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """FastAPI dependency for mandatory authenticated user."""
    if not authorization:
        raise UnauthorizedError("Authorization header is required")
    return await verify_supabase_token(authorization)


async def get_optional_user(authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    """FastAPI dependency for optional authenticated user."""
    if not authorization:
        return None
    try:
        return await verify_supabase_token(authorization)
    except Exception:
        return None


def rate_limit_public_verify(request: Request):
    """Dependency to rate-limit public verification requests."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    # Check X-Forwarded-For if behind a reverse proxy
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    public_verify_limiter.check(client_ip)
