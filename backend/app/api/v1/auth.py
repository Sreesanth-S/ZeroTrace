"""
User Identity and Account Management Endpoints
Supports user profile retrieval, account deactivation, and non-destructive soft deletion.
"""

from fastapi import APIRouter, Depends, status
from typing import Dict, Any

from backend.app.schemas.auth import (
    UserProfileResponse,
    AccountStatusUpdateRequest,
    ProfileUpdateRequest,
    SoftDeleteAccountRequest,
    LoginRequest,
    RegisterRequest,
    RefreshTokenRequest,
    AuthTokenResponse,
)
from backend.app.core.security import get_current_user
from backend.app.core.errors import EvidenceValidationError, UnauthorizedError
from backend.app.services.supabase_service import supabase_service

router = APIRouter(prefix="/auth", tags=["Authentication & Accounts"])


@router.post("/login", response_model=AuthTokenResponse)
async def login(body: LoginRequest):
    """Authenticate with email and password via Supabase Auth."""
    try:
        data = await supabase_service.auth_sign_in(body.email, body.password)
        return AuthTokenResponse(
            access_token=data["access_token"],
            token_type=data.get("token_type", "bearer"),
            expires_in=data.get("expires_in", 3600),
            refresh_token=data.get("refresh_token"),
            user=data.get("user", {})
        )
    except Exception as exc:
        raise UnauthorizedError(str(exc))


@router.post("/register")
async def register(body: RegisterRequest):
    """Register a new user account."""
    try:
        data = await supabase_service.auth_sign_up(body.email, body.password, body.full_name)
        return {
            "success": True,
            "message": "User registered successfully",
            "access_token": data.get("access_token"),
            "token_type": "bearer",
            "refresh_token": data.get("refresh_token"),
            "user": data.get("user", {})
        }
    except Exception as exc:
        raise EvidenceValidationError(str(exc))


@router.post("/refresh", response_model=AuthTokenResponse)
async def refresh_session(body: RefreshTokenRequest):
    """Refresh user session token."""
    try:
        data = await supabase_service.auth_refresh_token(body.refresh_token)
        return AuthTokenResponse(
            access_token=data["access_token"],
            token_type=data.get("token_type", "bearer"),
            expires_in=data.get("expires_in", 3600),
            refresh_token=data.get("refresh_token"),
            user=data.get("user", {})
        )
    except Exception as exc:
        raise UnauthorizedError(str(exc))


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieve the current authenticated user's account profile."""
    user_id = user["id"]
    email = user.get("email")

    profile = await supabase_service.get_user_profile(user_id)
    if not profile:
        profile = {}

    return UserProfileResponse(
        id=user_id,
        email=email,
        full_name=profile.get("full_name"),
        organization=profile.get("organization"),
        phone=profile.get("phone"),
        status=profile.get("status", "active"),
        created_at=profile.get("created_at")
    )


@router.patch("/profile")
async def update_my_profile(
    body: ProfileUpdateRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Update user profile fields such as full_name, organization, or phone."""
    user_id = user["id"]
    updates = {}
    if body.full_name is not None:
        updates["full_name"] = body.full_name.strip()
    if body.organization is not None:
        updates["organization"] = body.organization.strip()
    if body.phone is not None:
        updates["phone"] = body.phone.strip()

    result = await supabase_service.update_user_profile(user_id, updates)
    return {
        "success": True,
        "message": "Profile updated successfully",
        "profile": result.get("profile") or updates
    }


@router.patch("/account/status")
async def update_account_status(
    body: AccountStatusUpdateRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Deactivate or reactivate user account without affecting issued certificates."""
    user_id = user["id"]
    result = await supabase_service.update_user_status(user_id, body.status)
    return {
        "success": True,
        "message": f"Account status updated to '{body.status}'",
        "user_id": user_id,
        "status": body.status
    }


@router.post("/account/delete")
@router.delete("/account/delete")
async def soft_delete_account(
    body: SoftDeleteAccountRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Soft-delete account by marking user profile as deleted.
    Preserves historical certificate records and prevents cascade destruction of audit trails.
    """
    if body.confirmation != "DELETE MY ACCOUNT":
        raise EvidenceValidationError(
            "Confirmation text does not match required value 'DELETE MY ACCOUNT'."
        )

    user_id = user["id"]
    await supabase_service.update_user_status(user_id, "deleted")
    return {
        "success": True,
        "message": "Account has been deactivated and scheduled for soft-deletion. Historical certificates remain preserved for compliance.",
        "user_id": user_id,
        "status": "deleted"
    }
