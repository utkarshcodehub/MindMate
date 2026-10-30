"""
tests/test_auth.py

Unit and integration tests for Anonymous Device-Bound Token Authorization.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient



from api.auth import create_access_token, decode_access_token
from api.main import app

client = TestClient(app)


def test_jwt_token_encode_decode():
    user_id = "test-user-12345"
    token = create_access_token(user_id)
    assert token is not None
    assert isinstance(token, str)

    decoded_id = decode_access_token(token)
    assert decoded_id == user_id


def test_jwt_token_invalid():
    invalid_token = "invalid.token.value"
    decoded_id = decode_access_token(invalid_token)
    assert decoded_id is None


def test_unauthorized_access_denied():
    # Attempting to read user summary without token should return 401
    res = client.get("/api/user/some-random-user-id/summary")
    assert res.status_code == 401
    assert "Authorization token required" in res.json()["detail"]


def test_forbidden_access_other_user_logs():
    # User A creates a token
    user_a_id = "user-a-id"
    token_a = create_access_token(user_a_id)

    # User A tries to access User B's summary
    user_b_id = "user-b-id"
    res = client.get(
        f"/api/user/{user_b_id}/summary",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res.status_code == 403
    assert "Access denied" in res.json()["detail"]


def test_log_submission_forbidden_mismatch():
    user_a_id = "user-a-id"
    token_a = create_access_token(user_a_id)

    payload = {
        "user_id": "user-b-id",  # Mismatched user_id
        "log_date": "2026-07-26",
        "mood": 4,
        "sleep_hours": 7.0,
        "sleep_quality": 4,
        "study_hours": 4.0,
        "stress": 3,
        "free_text": None,
    }
    res = client.post(
        "/api/log",
        json=payload,
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res.status_code == 403
    assert "Access denied" in res.json()["detail"]


if __name__ == "__main__":
    print("Running authentication & authorization tests...")
    test_jwt_token_encode_decode()
    print("✓ test_jwt_token_encode_decode passed")
    test_jwt_token_invalid()
    print("✓ test_jwt_token_invalid passed")
    test_unauthorized_access_denied()
    print("✓ test_unauthorized_access_denied passed")
    test_forbidden_access_other_user_logs()
    print("✓ test_forbidden_access_other_user_logs passed")
    test_log_submission_forbidden_mismatch()
    print("✓ test_log_submission_forbidden_mismatch passed")
    print("ALL AUTH TESTS PASSED SUCCESSFULLY!")

