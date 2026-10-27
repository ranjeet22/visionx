"""
VisionX Authentication & Session Service
Implements Argon2id password hashing, cryptographic OTP generation,
session management, and MySQL database queries.
"""

import re
import secrets
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
import argon2

from backend import config
from backend.database import get_db_connection
from backend.services.email_service import send_otp_email

logger = logging.getLogger("visionx.auth")

# Password hasher configuration (Argon2id)
_PASSWORD_HASHER = argon2.PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    type=argon2.Type.ID
)

# Email format regex
_EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
# User ID regex: 3-32 characters, letters, digits, underscores, hyphens
_USER_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{3,32}$")


def hash_password(password: str) -> str:
    """Hashes a plaintext password using Argon2id."""
    return _PASSWORD_HASHER.hash(password)


def verify_password(password_hash: str, candidate_password: str) -> bool:
    """Verifies a plaintext password against an Argon2id hash."""
    try:
        return _PASSWORD_HASHER.verify(password_hash, candidate_password)
    except Exception:
        return False


def hash_otp(otp_code: str) -> str:
    """Derives a secure SHA-256 hash representation of the OTP code."""
    salt = config.SESSION_SECRET.encode("utf-8")
    return hashlib.sha256(salt + otp_code.encode("utf-8")).hexdigest()


def generate_otp_code() -> str:
    """Generates a cryptographically random 6-digit numeric OTP."""
    code_int = secrets.randbelow(900000) + 100000
    return str(code_int)


def validate_registration_inputs(
    user_id: str,
    email: str,
    password: str,
    confirm_password: str
) -> Tuple[bool, Optional[str]]:
    """Validates registration form inputs according to security guidelines."""
    uid = (user_id or "").strip()
    em = (email or "").strip().lower()

    if not _USER_ID_REGEX.match(uid):
        return False, "User ID must be 3-32 characters and contain only letters, numbers, underscores, or hyphens."

    if not _EMAIL_REGEX.match(em):
        return False, "Please enter a valid email address."

    if len(password) < 8:
        return False, "Password must be at least 8 characters long."

    if not any(c.isdigit() for c in password) or not any(c.isalpha() for c in password):
        return False, "Password must contain both letters and at least one number."

    if password != confirm_password:
        return False, "Password confirmation does not match."

    return True, None


def mask_email(email: str) -> str:
    """Masks an email for privacy-conscious display (e.g. u***@domain.com)."""
    if not email or "@" not in email:
        return "your email"
    user_part, domain_part = email.split("@", 1)
    if len(user_part) <= 2:
        masked_user = user_part[0] + "***"
    else:
        masked_user = user_part[0] + "***" + user_part[-1]
    return f"{masked_user}@{domain_part}"


def register_user(
    user_id: str,
    email: str,
    password: str,
    confirm_password: str
) -> Dict[str, Any]:
    """
    Registers a new user and sends an initial 6-digit OTP verification email.
    """
    is_valid, err_msg = validate_registration_inputs(user_id, email, password, confirm_password)
    if not is_valid:
        return {"success": False, "error": err_msg}

    norm_uid = user_id.strip()
    norm_email = email.strip().lower()

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Check for existing user by user_id or email
            cur.execute(
                "SELECT id, user_id, email, is_verified FROM users WHERE user_id = %s OR email = %s;",
                (norm_uid, norm_email)
            )
            existing = cur.fetchone()

            if existing:
                if existing["is_verified"]:
                    # Do not reveal whether user_id or email matched specifically
                    if existing["user_id"].lower() == norm_uid.lower():
                        return {"success": False, "error": "This User ID is already taken. Please choose another."}
                    else:
                        return {"success": False, "error": "An account with this email address already exists. Please log in."}
                else:
                    # Unverified user exists: update password and issue a fresh OTP
                    user_internal_id = existing["id"]
                    pwd_hash = hash_password(password)
                    cur.execute(
                        "UPDATE users SET password_hash = %s, user_id = %s, email = %s WHERE id = %s;",
                        (pwd_hash, norm_uid, norm_email, user_internal_id)
                    )
            else:
                # Create fresh unverified user
                pwd_hash = hash_password(password)
                cur.execute(
                    "INSERT INTO users (user_id, email, password_hash, is_verified) VALUES (%s, %s, %s, FALSE);",
                    (norm_uid, norm_email, pwd_hash)
                )
                user_internal_id = cur.lastrowid

            # Invalidate any previously issued OTPs for this user
            cur.execute(
                "UPDATE email_verifications SET is_used = TRUE WHERE user_id = %s AND is_used = FALSE;",
                (user_internal_id,)
            )

            # Generate new 6-digit OTP
            otp_plain = generate_otp_code()
            otp_hashed = hash_otp(otp_plain)
            now = datetime.now()
            expires_at = now + timedelta(minutes=5)
            cooldown_until = now + timedelta(seconds=60)

            cur.execute(
                """
                INSERT INTO email_verifications 
                (user_id, otp_hash, expires_at, attempts, resend_cooldown_until, is_used)
                VALUES (%s, %s, %s, 0, %s, FALSE);
                """,
                (user_internal_id, otp_hashed, expires_at, cooldown_until)
            )

    # Deliver OTP email
    send_ok, send_info, dev_otp = send_otp_email(norm_email, norm_uid, otp_plain)

    return {
        "success": True,
        "message": "Registration initiated. Please verify your email with the 6-digit OTP sent to your inbox.",
        "user_id": norm_uid,
        "email": norm_email,
        "masked_email": mask_email(norm_email),
        "cooldown_seconds": 60,
        "expires_in_minutes": 5,
        "email_delivery": {
            "success": send_ok,
            "info": send_info,
            "dev_otp": dev_otp,
            "smtp_configured": bool(config.SMTP_HOST and config.SMTP_HOST.strip())
        }
    }


def verify_otp(identifier: str, otp_code: str) -> Dict[str, Any]:
    """
    Verifies the 6-digit OTP code, marks user as verified, and activates session.
    """
    clean_id = (identifier or "").strip().lower()
    clean_otp = (otp_code or "").strip()

    if not clean_otp or len(clean_otp) != 6 or not clean_otp.isdigit():
        return {"success": False, "error": "Please enter a valid 6-digit verification code."}

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Find user
            cur.execute(
                "SELECT id, user_id, email, is_verified FROM users WHERE LOWER(user_id) = %s OR LOWER(email) = %s;",
                (clean_id, clean_id)
            )
            user = cur.fetchone()

            if not user:
                return {"success": False, "error": "User account not found. Please register first."}

            if user["is_verified"]:
                return {
                    "success": True,
                    "message": "Account is already verified. You can proceed to log in.",
                    "user": {"id": user["id"], "user_id": user["user_id"], "email": user["email"]},
                    "already_verified": True
                }

            user_internal_id = user["id"]

            # Retrieve active OTP record
            cur.execute(
                """
                SELECT id, otp_hash, expires_at, attempts, is_used 
                FROM email_verifications 
                WHERE user_id = %s AND is_used = FALSE 
                ORDER BY id DESC LIMIT 1;
                """,
                (user_internal_id,)
            )
            otp_record = cur.fetchone()

            if not otp_record:
                return {"success": False, "error": "No active verification code found. Please request a new code."}

            # Check attempt limit (max 5)
            if otp_record["attempts"] >= 5:
                cur.execute("UPDATE email_verifications SET is_used = TRUE WHERE id = %s;", (otp_record["id"],))
                return {"success": False, "error": "Too many failed attempts. This code is invalidated. Please request a new code."}

            # Check expiry
            now = datetime.now()
            if now > otp_record["expires_at"]:
                cur.execute("UPDATE email_verifications SET is_used = TRUE WHERE id = %s;", (otp_record["id"],))
                return {"success": False, "error": "Verification code has expired. Please request a new code."}

            # Verify OTP hash
            candidate_hash = hash_otp(clean_otp)
            if not secrets.compare_digest(otp_record["otp_hash"], candidate_hash):
                new_attempts = otp_record["attempts"] + 1
                cur.execute(
                    "UPDATE email_verifications SET attempts = %s WHERE id = %s;",
                    (new_attempts, otp_record["id"])
                )
                remaining = max(0, 5 - new_attempts)
                return {"success": False, "error": f"Invalid verification code. {remaining} attempt(s) remaining."}

            # Successful verification: Mark OTP as used and user as verified
            cur.execute("UPDATE email_verifications SET is_used = TRUE WHERE id = %s;", (otp_record["id"],))
            cur.execute("UPDATE users SET is_verified = TRUE WHERE id = %s;", (user_internal_id,))

            # Create an authenticated session
            session_id = secrets.token_urlsafe(48)
            session_expires = now + timedelta(seconds=config.SESSION_MAX_AGE_SECONDS)
            cur.execute(
                "INSERT INTO user_sessions (session_id, user_id, expires_at) VALUES (%s, %s, %s);",
                (session_id, user_internal_id, session_expires)
            )

    return {
        "success": True,
        "message": "Account successfully verified and activated!",
        "session_id": session_id,
        "user": {
            "id": user["id"],
            "user_id": user["user_id"],
            "email": user["email"],
            "is_verified": True
        }
    }


def resend_otp(identifier: str) -> Dict[str, Any]:
    """
    Resends a fresh 6-digit OTP code subject to a 60-second cooldown period.
    """
    clean_id = (identifier or "").strip().lower()

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, email, is_verified FROM users WHERE LOWER(user_id) = %s OR LOWER(email) = %s;",
                (clean_id, clean_id)
            )
            user = cur.fetchone()

            if not user:
                # Avoid detailed account disclosure
                return {"success": False, "error": "Account not found. Please register first."}

            if user["is_verified"]:
                return {"success": False, "error": "This account is already verified. Please log in directly."}

            user_internal_id = user["id"]

            # Check cooldown against latest OTP record
            cur.execute(
                """
                SELECT resend_cooldown_until FROM email_verifications 
                WHERE user_id = %s 
                ORDER BY id DESC LIMIT 1;
                """,
                (user_internal_id,)
            )
            latest = cur.fetchone()

            now = datetime.now()
            if latest and latest.get("resend_cooldown_until"):
                cooldown_time = latest["resend_cooldown_until"]
                if now < cooldown_time:
                    remaining_sec = max(1, int((cooldown_time - now).total_seconds()))
                    return {
                        "success": False,
                        "error": f"Please wait {remaining_sec} seconds before requesting a new code.",
                        "cooldown_remaining": remaining_sec
                    }

            # Invalidate older active OTPs
            cur.execute(
                "UPDATE email_verifications SET is_used = TRUE WHERE user_id = %s AND is_used = FALSE;",
                (user_internal_id,)
            )

            # Generate new OTP
            otp_plain = generate_otp_code()
            otp_hashed = hash_otp(otp_plain)
            expires_at = now + timedelta(minutes=5)
            cooldown_until = now + timedelta(seconds=60)

            cur.execute(
                """
                INSERT INTO email_verifications 
                (user_id, otp_hash, expires_at, attempts, resend_cooldown_until, is_used)
                VALUES (%s, %s, %s, 0, %s, FALSE);
                """,
                (user_internal_id, otp_hashed, expires_at, cooldown_until)
            )

    send_ok, send_info, dev_otp = send_otp_email(user["email"], user["user_id"], otp_plain)

    return {
        "success": True,
        "message": "A fresh 6-digit verification code has been dispatched.",
        "masked_email": mask_email(user["email"]),
        "cooldown_seconds": 60,
        "email_delivery": {
            "success": send_ok,
            "info": send_info,
            "dev_otp": dev_otp,
            "smtp_configured": bool(config.SMTP_HOST and config.SMTP_HOST.strip())
        }
    }


def authenticate_user(identifier: str, candidate_password: str) -> Dict[str, Any]:
    """
    Authenticates a user via User ID or Email and password.
    Returns session_id and user details on success.
    """
    clean_id = (identifier or "").strip().lower()

    if not clean_id or not candidate_password:
        return {"success": False, "error": "Please provide both User ID/Email and password."}

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, email, password_hash, is_verified FROM users WHERE LOWER(user_id) = %s OR LOWER(email) = %s;",
                (clean_id, clean_id)
            )
            user = cur.fetchone()

            # Non-revealing error message
            generic_err = "Invalid credentials. Please verify your User ID/email and password."

            if not user:
                return {"success": False, "error": generic_err}

            if not verify_password(user["password_hash"], candidate_password):
                return {"success": False, "error": generic_err}

            if not user["is_verified"]:
                return {
                    "success": False,
                    "error": "Your account is not verified yet. Please enter the OTP sent to your email.",
                    "requires_verification": True,
                    "user_id": user["user_id"],
                    "email": user["email"],
                    "masked_email": mask_email(user["email"])
                }

            user_internal_id = user["id"]
            now = datetime.now()

            # Update last_login_at
            cur.execute("UPDATE users SET last_login_at = %s WHERE id = %s;", (now, user_internal_id))

            # Create new session
            session_id = secrets.token_urlsafe(48)
            session_expires = now + timedelta(seconds=config.SESSION_MAX_AGE_SECONDS)
            cur.execute(
                "INSERT INTO user_sessions (session_id, user_id, expires_at) VALUES (%s, %s, %s);",
                (session_id, user_internal_id, session_expires)
            )

    return {
        "success": True,
        "message": "Login successful.",
        "session_id": session_id,
        "user": {
            "id": user["id"],
            "user_id": user["user_id"],
            "email": user["email"],
            "is_verified": True
        }
    }


def get_user_from_session(session_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Validates the session token from the HttpOnly cookie and returns safe user information.
    """
    if not session_id or not session_id.strip():
        return None

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT s.session_id, s.expires_at, u.id, u.user_id, u.email, u.is_verified, u.created_at, u.last_login_at
                    FROM user_sessions s
                    JOIN users u ON s.user_id = u.id
                    WHERE s.session_id = %s;
                    """,
                    (session_id.strip(),)
                )
                record = cur.fetchone()

                if not record:
                    return None

                now = datetime.now()
                if now > record["expires_at"]:
                    # Clean up expired session
                    cur.execute("DELETE FROM user_sessions WHERE session_id = %s;", (session_id.strip(),))
                    return None

                # Refresh last_activity_at
                cur.execute(
                    "UPDATE user_sessions SET last_activity_at = %s WHERE session_id = %s;",
                    (now, session_id.strip())
                )

                return {
                    "id": record["id"],
                    "user_id": record["user_id"],
                    "email": record["email"],
                    "is_verified": bool(record["is_verified"]),
                    "created_at": str(record["created_at"]),
                    "last_login_at": str(record["last_login_at"]) if record["last_login_at"] else None
                }
    except Exception as e:
        logger.error(f"Session lookup error: {e}")
        return None


def terminate_session(session_id: Optional[str]) -> bool:
    """Invalidates and removes an active session."""
    if not session_id:
        return True

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM user_sessions WHERE session_id = %s;", (session_id.strip(),))
        return True
    except Exception as e:
        logger.error(f"Error terminating session: {e}")
        return False
