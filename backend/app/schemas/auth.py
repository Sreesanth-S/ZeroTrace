"""
Authentication and User Profile Schemas
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field


UserAccountStatus = Literal["active", "deactivated", "deleted"]


class UserProfileResponse(BaseModel):
    id: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    organization: Optional[str] = None
    phone: Optional[str] = None
    status: UserAccountStatus = "active"
    created_at: Optional[str] = None


class AccountStatusUpdateRequest(BaseModel):
    status: Literal["active", "deactivated"] = Field(..., description="Target status: active or deactivated")
    reason: Optional[str] = Field(None, description="Optional reason for deactivation")


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, description="Updated full name")
    organization: Optional[str] = Field(None, description="Updated organization")
    phone: Optional[str] = Field(None, description="Updated phone number")


class SoftDeleteAccountRequest(BaseModel):
    confirmation: str = Field(..., description="Must equal 'DELETE MY ACCOUNT' to confirm soft deletion")


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User account password")


class RegisterRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="User password (min 6 chars)")
    full_name: Optional[str] = Field(None, description="Full name or organization name")


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Supabase refresh token")


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    refresh_token: Optional[str] = None
    user: dict
