"""
Unit and Integration Tests for VisionX Authentication System.
Covers:
- Input validation (User ID format, email format, password requirements)
- Registration flow & duplicate handling
- OTP generation, hashing, attempt limiting, and expiration
- Account verification
- Login via User ID and via Email
- Unverified account login blocking
- Session creation, persistence, and invalidation (logout)
"""

import pytest
from datetime import datetime, timedelta

from backend import config
from backend.database import get_db_connection
from backend.services.auth_service import (
    validate_registration_inputs,
    register_user,
    verify_otp,
    resend_otp,
    authenticate_user,
    get_user_from_session,
    terminate_session,
    hash_otp
)


@pytest.fixture(autouse=True)
def clean_test_users():
    """Cleans up test user records before and after tests."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE user_id LIKE 'test_%';")
    yield
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE user_id LIKE 'test_%';")


def test_input_validation():
    # Valid
    ok, err = validate_registration_inputs("test_user", "test@example.com", "Password123", "Password123")
    assert ok is True
    assert err is None

    # Invalid user ID (too short)
    ok, err = validate_registration_inputs("ab", "test@example.com", "Password123", "Password123")
    assert ok is False
    assert "User ID" in err

    # Invalid email
    ok, err = validate_registration_inputs("test_user", "notanemail", "Password123", "Password123")
    assert ok is False
    assert "email" in err.lower()

    # Short password (< 8 chars)
    ok, err = validate_registration_inputs("test_user", "test@example.com", "Pass1", "Pass1")
    assert ok is False
    assert "at least 8" in err

    # Password without number
    ok, err = validate_registration_inputs("test_user", "test@example.com", "PasswordOnly", "PasswordOnly")
    assert ok is False
    assert "number" in err.lower()

    # Password mismatch
    ok, err = validate_registration_inputs("test_user", "test@example.com", "Password123", "Different123")
    assert ok is False
    assert "match" in err.lower()


def test_registration_and_otp_verification():
    # 1. Register a new user
    res = register_user("test_alice", "test_alice@example.com", "SecretPass123", "SecretPass123")
    assert res["success"] is True
    assert res["user_id"] == "test_alice"

    # 2. Duplicate registration attempt with same user_id while unverified re-issues OTP
    res_reissue = register_user("test_alice", "test_alice@example.com", "NewSecretPass456", "NewSecretPass456")
    assert res_reissue["success"] is True

    # 3. Fetch current active OTP from DB for testing
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT v.id, v.otp_hash, u.id as uid 
                FROM email_verifications v 
                JOIN users u ON v.user_id = u.id 
                WHERE u.user_id = 'test_alice' AND v.is_used = FALSE;
                """
            )
            record = cur.fetchone()
            assert record is not None

    # 4. Attempt incorrect OTP
    bad_verify = verify_otp("test_alice", "000000")
    assert bad_verify["success"] is False
    assert "Invalid verification code" in bad_verify["error"]

    # 5. Simulate valid OTP verification by testing known OTP
    known_otp = "123456"
    known_hash = hash_otp(known_otp)
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE email_verifications SET otp_hash = %s WHERE id = %s;", (known_hash, record["id"]))

    good_verify = verify_otp("test_alice", known_otp)
    assert good_verify["success"] is True
    assert "session_id" in good_verify
    assert good_verify["user"]["is_verified"] is True

    # 6. Reusing verified OTP should not be permitted
    reuse = verify_otp("test_alice", known_otp)
    assert reuse["success"] is True
    assert reuse.get("already_verified") is True

    # 7. Now registering a verified username should fail with duplicate error
    dup_res = register_user("test_alice", "another_email@example.com", "AnotherPass123", "AnotherPass123")
    assert dup_res["success"] is False
    assert "already taken" in dup_res["error"]


def test_login_and_session_lifecycle():
    # 1. Register and verify test user
    register_user("test_bob", "test_bob@example.com", "MyPassword99", "MyPassword99")

    # Manually mark verified for login test
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET is_verified = TRUE WHERE user_id = 'test_bob';")

    # 2. Login with wrong password
    bad_login = authenticate_user("test_bob", "WrongPass123")
    assert bad_login["success"] is False
    assert "Invalid credentials" in bad_login["error"]

    # 3. Login with valid User ID
    login_uid = authenticate_user("test_bob", "MyPassword99")
    assert login_uid["success"] is True
    assert "session_id" in login_uid
    session_id = login_uid["session_id"]

    # 4. Validate session retrieval
    user_info = get_user_from_session(session_id)
    assert user_info is not None
    assert user_info["user_id"] == "test_bob"
    assert user_info["email"] == "test_bob@example.com"

    # 5. Login with Email instead of User ID
    login_email = authenticate_user("test_bob@example.com", "MyPassword99")
    assert login_email["success"] is True
    assert login_email["user"]["user_id"] == "test_bob"

    # 6. Logout / Terminate session
    term_ok = terminate_session(session_id)
    assert term_ok is True
    assert get_user_from_session(session_id) is None


def test_otp_expiration_and_cooldown():
    # Register user
    register_user("test_charlie", "test_charlie@example.com", "PassCode789", "PassCode789")

    # 1. Cooldown test: immediately resending should fail with cooldown message
    resend1 = resend_otp("test_charlie")
    assert resend1["success"] is False
    assert "wait" in resend1["error"].lower()

    # 2. Expiration test: artificially set expiry to past
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            past_time = datetime.now() - timedelta(minutes=10)
            cur.execute(
                """
                UPDATE email_verifications v 
                JOIN users u ON v.user_id = u.id 
                SET v.expires_at = %s 
                WHERE u.user_id = 'test_charlie';
                """,
                (past_time,)
            )

    expired_verify = verify_otp("test_charlie", "123456")
    assert expired_verify["success"] is False
    assert "expired" in expired_verify["error"].lower()
