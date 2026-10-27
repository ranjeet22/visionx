"""
VisionX Authentication Pydantic Schemas
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr


class RegisterRequest(BaseModel):
    user_id: str = Field(..., min_length=3, max_length=32, description="Unique username / user ID")
    email: str = Field(..., description="Valid email address")
    password: str = Field(..., min_length=8, description="Password (at least 8 chars, letters and numbers)")
    confirm_password: str = Field(..., min_length=8, description="Must match password")


class VerifyOtpRequest(BaseModel):
    identifier: str = Field(..., description="User ID or Email address")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit numeric OTP code")


class ResendOtpRequest(BaseModel):
    identifier: str = Field(..., description="User ID or Email address")


class LoginRequest(BaseModel):
    identifier: str = Field(..., description="User ID or Email address")
    password: str = Field(..., description="Password")


class UserProfile(BaseModel):
    id: int
    user_id: str
    email: str
    is_verified: bool = True
    created_at: Optional[str] = None
    last_login_at: Optional[str] = None


class AuthResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    user: Optional[UserProfile] = None
    requires_verification: Optional[bool] = False
    masked_email: Optional[str] = None
    cooldown_seconds: Optional[int] = None
    email_delivery: Optional[Dict[str, Any]] = None
