"""
Auth router — login, current user, logout.

Exposes:
- POST /api/auth/login   → exchange email+password for a JWT
- GET  /api/auth/me      → get info about the currently logged-in user
- POST /api/auth/logout  → revoke the current session

💡 CONCEPT: Different endpoints, different auth requirements
   - `login` is PUBLIC (no token needed — that's how you GET a token)
   - `me` and `logout` are PROTECTED (require a valid token)

   This is expressed via `Depends(get_current_user)` on the protected
   endpoints. FastAPI handles the 401 response if the token is missing
   or invalid.
"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Request, status

from app import security
from app.config import settings
from app.dependencies import BearerCredentials, CurrentUser, DbSession
from app.schemas.auth import (
    LoginRequest,
    LogoutResponse,
    TokenResponse,
    UserResponse,
)
from app.services import auth as auth_service

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
)


# ============================================================
# POST /api/auth/login
# ============================================================

@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: DbSession,
) -> TokenResponse:
    """Authenticate with email + password. Returns a JWT on success.

    💡 CONCEPT: FastAPI's `Request` object
       Gives access to low-level HTTP info (headers, client IP, etc.)
       that Pydantic doesn't surface in the body. We use it here to
       capture the User-Agent and IP for the session row — useful later
       for the "active sessions" UI in settings.
    """
    user = auth_service.authenticate_user(
        db,
        email=payload.email,
        password=payload.password,
    )
    if user is None:
        # Intentionally vague — don't leak whether the email exists
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Create a DB-tracked session so we can revoke it later
    raw_session_token, session_row = auth_service.create_session(
        db,
        user=user,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )

    # Pack the session token into a JWT for the client
    access_token = security.create_access_token(
        user_id=user.id,
        session_token=raw_session_token,
    )

    # Compute expiration for the response (same as the one embedded in the JWT)
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    return TokenResponse(
        access_token=access_token,
        expires_at=expires_at,
    )


# ============================================================
# GET /api/auth/me
# ============================================================

@router.get("/me", response_model=UserResponse)
def me(user: CurrentUser) -> UserResponse:
    """Return info about the currently authenticated user.

    The `CurrentUser` dependency does all the work: it extracts the JWT,
    verifies the signature, looks up the session and user, and raises
    401 if anything is wrong. By the time we get here, `user` is valid.
    """
    return UserResponse.model_validate(user)


# ============================================================
# POST /api/auth/logout
# ============================================================

@router.post("/logout", response_model=LogoutResponse)
def logout(
    credentials: BearerCredentials,
    db: DbSession,
) -> LogoutResponse:
    """Revoke the current session.

    After this call, the JWT still exists on the client but the session
    row is gone, so any future use fails at `get_user_from_jwt`.

    💡 CONCEPT: Why not require `CurrentUser` here?
       Logout should be lenient: if the token is already expired, we
       still want to return success (not 401). The frontend calls
       logout during cleanup even with stale tokens.

       So we just try to revoke. Success or not-found both return 200.
    """
    if credentials:
        auth_service.revoke_session(db, jwt_token=credentials.credentials)
    return LogoutResponse()
