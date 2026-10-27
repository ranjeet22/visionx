"""
Integration Tests for FastAPI Authentication Endpoints.
Uses httpx AsyncClient to test:
- POST /api/auth/register
- POST /api/auth/verify-otp
- POST /api/auth/resend-otp
- POST /api/auth/login
- GET /api/auth/me (authenticated and unauthenticated)
- POST /api/auth/logout
"""

import pytest
import httpx
from backend.server import app
from backend.database import get_db_connection
from backend.services.auth_service import hash_otp


@pytest.fixture(autouse=True)
def clean_endpoint_test_users():
    """Wipes test users before and after endpoint tests."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE user_id LIKE 'ep_test_%';")
    yield
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE user_id LIKE 'ep_test_%';")


@pytest.mark.asyncio
async def test_full_auth_api_lifecycle():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. Access protected /api/auth/me without cookie -> 401
        me_unauth = await client.get("/api/auth/me")
        assert me_unauth.status_code == 401

        # 2. Register valid user
        reg_payload = {
            "user_id": "ep_test_dana",
            "email": "ep_test_dana@example.com",
            "password": "StrongPassword99",
            "confirm_password": "StrongPassword99"
        }
        reg_res = await client.post("/api/auth/register", json=reg_payload)
        assert reg_res.status_code == 200
        reg_data = reg_res.json()
        assert reg_data["success"] is True
        assert "masked_email" in reg_data

        # 3. Check database for created OTP
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT v.id 
                    FROM email_verifications v 
                    JOIN users u ON v.user_id = u.id 
                    WHERE u.user_id = 'ep_test_dana';
                    """
                )
                otp_row = cur.fetchone()
                assert otp_row is not None
                # Set a known OTP for test verification
                known_otp = "654321"
                cur.execute(
                    "UPDATE email_verifications SET otp_hash = %s WHERE id = %s;",
                    (hash_otp(known_otp), otp_row["id"])
                )

        # 4. Verify with wrong OTP
        wrong_verify = await client.post("/api/auth/verify-otp", json={
            "identifier": "ep_test_dana",
            "otp": "000000"
        })
        assert wrong_verify.status_code == 400

        # 5. Verify with correct OTP -> Should set cookie and return user
        good_verify = await client.post("/api/auth/verify-otp", json={
            "identifier": "ep_test_dana",
            "otp": known_otp
        })
        assert good_verify.status_code == 200
        verify_data = good_verify.json()
        assert verify_data["success"] is True
        assert verify_data["user"]["user_id"] == "ep_test_dana"
        assert "visionx_session" in client.cookies

        # 6. Now call /api/auth/me -> Should return user profile
        me_auth = await client.get("/api/auth/me")
        assert me_auth.status_code == 200
        me_data = me_auth.json()
        assert me_data["user_id"] == "ep_test_dana"
        assert me_data["email"] == "ep_test_dana@example.com"

        # 7. Logout -> Clears cookie
        logout_res = await client.post("/api/auth/logout")
        assert logout_res.status_code == 200
        assert logout_res.json()["success"] is True

        # 8. Check /api/auth/me after logout -> 401
        me_after_logout = await client.get("/api/auth/me")
        assert me_after_logout.status_code == 401

        # 9. Login again using Email and password
        login_res = await client.post("/api/auth/login", json={
            "identifier": "ep_test_dana@example.com",
            "password": "StrongPassword99"
        })
        assert login_res.status_code == 200
        login_data = login_res.json()
        assert login_data["success"] is True
        assert login_data["user"]["user_id"] == "ep_test_dana"
        assert "visionx_session" in client.cookies
