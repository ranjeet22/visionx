"""
VisionX Authentication API Routes
Endpoints:
- POST /api/auth/register
- POST /api/auth/verify-otp
- POST /api/auth/resend-otp
- POST /api/auth/login
- POST /api/auth/logout
- GET /api/auth/me
"""

import logging
from typing import Optional
from fastapi import APIRouter, Request, Response, HTTPException, status, Depends

from backend import config
from backend.schemas.auth import (
    RegisterRequest,
    VerifyOtpRequest,
    ResendOtpRequest,
    LoginRequest,
    AuthResponse,
    UserProfile
)
from backend.services.auth_service import (
    register_user,
    verify_otp,
    resend_otp,
    authenticate_user,
    get_user_from_session,
    terminate_session
)

logger = logging.getLogger("visionx.auth_router")

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def set_auth_cookie(response: Response, session_id: str):
    """Sets a secure HttpOnly session cookie on the response."""
    response.set_cookie(
        key=config.SESSION_COOKIE_NAME,
        value=session_id,
        max_age=config.SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=config.COOKIE_SECURE,
        samesite=config.COOKIE_SAMESITE,
        path="/"
    )


def clear_auth_cookie(response: Response):
    """Clears the session cookie on logout."""
    response.delete_cookie(
        key=config.SESSION_COOKIE_NAME,
        path="/"
    )


def get_current_user(request: Request) -> Optional[dict]:
    """Dependency: retrieves authenticated user from HttpOnly session cookie."""
    session_id = request.cookies.get(config.SESSION_COOKIE_NAME)
    if not session_id:
        return None
    return get_user_from_session(session_id)


def require_authenticated_user(request: Request) -> dict:
    """Dependency: raises 401 Unauthorized if request has no active valid session."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in."
        )
    return user


@router.post("/register", response_model=AuthResponse)
async def api_register(payload: RegisterRequest):
    """
    Validates registration form, creates unverified user, and issues a 6-digit OTP email.
    """
    result = register_user(
        user_id=payload.user_id,
        email=payload.email,
        password=payload.password,
        confirm_password=payload.confirm_password
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return AuthResponse(
        success=True,
        message=result["message"],
        masked_email=result["masked_email"],
        cooldown_seconds=result["cooldown_seconds"],
        email_delivery=result.get("email_delivery")
    )


@router.post("/verify-otp", response_model=AuthResponse)
async def api_verify_otp(payload: VerifyOtpRequest, response: Response):
    """
    Verifies the submitted 6-digit OTP code.
    On success, activates the account and creates an authenticated session.
    """
    result = verify_otp(
        identifier=payload.identifier,
        otp_code=payload.otp
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    # If verification generated an active session, attach HttpOnly cookie
    if result.get("session_id"):
        set_auth_cookie(response, result["session_id"])

    user_data = result.get("user")
    user_profile = UserProfile(**user_data) if user_data else None

    return AuthResponse(
        success=True,
        message=result["message"],
        user=user_profile
    )


@router.post("/resend-otp", response_model=AuthResponse)
async def api_resend_otp(payload: ResendOtpRequest):
    """
    Resends a fresh 6-digit OTP code subject to a 60-second cooldown period.
    """
    result = resend_otp(identifier=payload.identifier)

    if not result["success"]:
        raise HTTPException(
            status_code=429 if result.get("cooldown_remaining") else 400,
            detail=result["error"]
        )

    return AuthResponse(
        success=True,
        message=result["message"],
        masked_email=result["masked_email"],
        cooldown_seconds=result["cooldown_seconds"],
        email_delivery=result.get("email_delivery")
    )


@router.post("/login", response_model=AuthResponse)
async def api_login(payload: LoginRequest, response: Response):
    """
    Authenticates user via User ID or Email and password.
    Sets HttpOnly session cookie on success.
    """
    result = authenticate_user(
        identifier=payload.identifier,
        candidate_password=payload.password
    )

    if not result["success"]:
        if result.get("requires_verification"):
            # Return 403 with context indicating OTP verification is needed
            return AuthResponse(
                success=False,
                error=result["error"],
                requires_verification=True,
                masked_email=result.get("masked_email")
            )
        raise HTTPException(status_code=401, detail=result["error"])

    # Set authenticated session cookie
    set_auth_cookie(response, result["session_id"])

    user_data = result.get("user")
    user_profile = UserProfile(**user_data) if user_data else None

    return AuthResponse(
        success=True,
        message=result["message"],
        user=user_profile
    )


@router.post("/logout", response_model=AuthResponse)
async def api_logout(request: Request, response: Response):
    """
    Terminates active session in MySQL and clears the HttpOnly session cookie.
    """
    session_id = request.cookies.get(config.SESSION_COOKIE_NAME)
    terminate_session(session_id)
    clear_auth_cookie(response)

    return AuthResponse(
        success=True,
        message="Logged out successfully."
    )


@router.get("/me", response_model=UserProfile)
async def api_me(user: dict = Depends(require_authenticated_user)):
    """
    Returns the authenticated user's profile information.
    Protected endpoint: requires a valid active session.
    """
    return UserProfile(
        id=user["id"],
        user_id=user["user_id"],
        email=user["email"],
        is_verified=user["is_verified"],
        created_at=user.get("created_at"),
        last_login_at=user.get("last_login_at")
    )
