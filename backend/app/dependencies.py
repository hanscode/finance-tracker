"""
FastAPI dependencies — reusable building blocks for endpoints.

💡 CONCEPT: Dependencies chain
   FastAPI's dependency system lets us compose reusable pieces:

       get_db  ─┐
                ├──▶ get_current_user ──▶ require_owner ──▶ endpoint
       oauth2 ─┘

   Each layer can have its own failure path (401 for invalid token,
   403 for insufficient role). Endpoints just declare what they need.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserRole
from app.services import auth as auth_service

# ============================================================
# HTTPBearer scheme — extracts "Authorization: Bearer <token>" headers
# ============================================================
#
# 💡 CONCEPT: HTTPBearer vs OAuth2PasswordBearer
#    FastAPI ships two bearer-token helpers:
#
#    - OAuth2PasswordBearer: Swagger shows a LOGIN FORM (username + password)
#      and posts them as form-encoded data to `tokenUrl`. Only useful if
#      your login endpoint accepts form data.
#
#    - HTTPBearer: Swagger shows a TOKEN FIELD. You paste a token you
#      already obtained (e.g., from POST /api/auth/login in Swagger).
#      Works with any login format, including our JSON endpoint.
#
#    We chose HTTPBearer because /api/auth/login takes JSON (validated by
#    Pydantic), not form-encoded data.
bearer_scheme = HTTPBearer(
    bearerFormat="JWT",
    description=(
        "Paste an access_token from POST /api/auth/login "
        "(no 'Bearer ' prefix — Swagger adds it automatically)."
    ),
    auto_error=False,  # Don't raise on missing token; we handle that below
)


# ============================================================
# Type aliases (just for readability)
# ============================================================

DbSession = Annotated[Session, Depends(get_db)]
# HTTPBearer returns an HTTPAuthorizationCredentials object with:
#   .scheme      → "Bearer"
#   .credentials → the actual token string
BearerCredentials = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(bearer_scheme),
]


# ============================================================
# Authentication dependency
# ============================================================

def get_current_user(
    credentials: BearerCredentials,
    db: DbSession,
) -> User:
    """Resolve the currently authenticated user, or raise 401.

    Use it in any endpoint that requires auth:

        @router.get("/me")
        def me(user: User = Depends(get_current_user)):
            return user

    Raises:
        HTTPException 401: missing, invalid, expired, or revoked token.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = auth_service.get_user_from_jwt(db, jwt_token=credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


# ============================================================
# Role-based dependencies
# ============================================================
#
# 💡 CONCEPT: Dependencies that depend on other dependencies
#    `require_owner` doesn't know how to decode JWTs. It just takes a
#    User (provided by get_current_user) and checks the role.
#
#    FastAPI resolves the chain automatically:
#      request → oauth2_scheme → get_current_user → require_owner → endpoint


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_owner(user: CurrentUser) -> User:
    """Allow only the owner (full control) through."""
    if user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the account owner can perform this action.",
        )
    return user


def require_admin_or_owner(user: CurrentUser) -> User:
    """Allow owner or admin (admin-level access)."""
    if user.role not in (UserRole.OWNER, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires admin or owner role.",
        )
    return user
