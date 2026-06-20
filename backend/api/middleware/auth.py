"""
Firebase Auth middleware.

Verifies the Firebase ID token sent in the Auth header.
Set REQUIRE_AUTH=false in your .env to skip verification locally.

For production:
  1. User signs in with Google SSO on the frontend (Firebase SDK)
  2. Frontend gets an ID token from Firebase
  3. Frontend sends: Authorization: Bearer <id_token>
  4. This middleware verifies the token against Firebase
  5. Injects the decoded user info into the request state
"""
import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.config import settings

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticatedUser:
    """Decoded Firebase user info attached to each request."""

    def __init__(self, uid: str, email: Optional[str], name: Optional[str]):
        self.uid = uid
        self.email = email
        self.name = name

    def __repr__(self) -> str:
        return f"AuthenticatedUser(uid={self.uid}, email={self.email})"


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[AuthenticatedUser]:
    """
    FastAPI dependency — inject into any route that needs auth.

    Usage:
        @router.post("/query")
        async def query(user: AuthenticatedUser = Depends(get_current_user)):
            ...

    Returns local-dev user if REQUIRE_AUTH=false.
    Raises 401 if token is missing or invalid in production.
    """
    # For Loc dev — skip auth entirely
    if not settings.require_auth:
        return AuthenticatedUser(uid="local-dev", email=None, name="Local Dev")

    # For Prod — verifies Firebase ID token
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header. Expected: Bearer <firebase_id_token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        import firebase_admin
        from firebase_admin import auth as firebase_auth, credentials as fb_creds

        if not firebase_admin._apps:
            if settings.firebase_credentials_path:
                cred = fb_creds.Certificate(settings.firebase_credentials_path)
            else:
                cred = fb_creds.ApplicationDefault()
            firebase_admin.initialize_app(cred)

        decoded = firebase_auth.verify_id_token(token)

        return AuthenticatedUser(
            uid=decoded["uid"],
            email=decoded.get("email"),
            name=decoded.get("name"),
        )

    except Exception as exc:
        logger.warning(f"Token verification failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )