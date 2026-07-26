
"""
api/auth.py

Anonymous Device-Bound Token Authorization.

Generates and verifies long-lived JWT access tokens bound to each student's user_id.
Enforces that students can access ONLY their own logs and records without needing
a traditional login/password screen every visit ("open space concept").
"""

import os
import time
import jwt
from typing import Optional
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

_JWT_SECRET = os.environ.get(
    "JWT_SECRET",
    "student-wellness-jwt-secret-open-space-key-2026"
)
_ALGORITHM = "HS256"

security = HTTPBearer(auto_error=False)


def create_access_token(user_id: str) -> str:
    """
    Generate a signed JWT token bound to the specified user_id.
    Valid long-term so device-bound storage in localStorage maintains seamless access.
    """
    payload = {
        "sub": user_id,
        "iat": int(time.time()),
        "type": "device_bound_anonymous",
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> Optional[str]:
    """
    Decode and verify JWT signature, returning the bound user_id (sub).
    Returns None if token is invalid or tampered with.
    """
    try:
        payload = jwt.decode(token, _JWT_SECRET, algorithms=[_ALGORITHM])
        return payload.get("sub")
    except (jwt.PyJWTError, Exception):
        return None


def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> str:
    """
    FastAPI dependency to extract and verify the Bearer token from the request header.
    Raises 401 Unauthorized if missing or invalid.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token required. Please complete onboarding or check credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = decode_access_token(credentials.credentials)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authorization token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_id


def verify_user_access(
    user_id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> str:
    """
    Dependency helper to enforce that the requesting token's user_id matches the target user_id.
    Raises 403 Forbidden if attempting to access another user's logs.
    """
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only access your own logs.",
        )
    return current_user_id
