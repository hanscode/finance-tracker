"""Pydantic schemas — request/response validation for HTTP endpoints."""

from app.schemas.auth import (
    LoginRequest,
    LogoutResponse,
    TokenResponse,
    UserResponse,
)
from app.schemas.category import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
)
from app.schemas.setup import (
    SetupRequest,
    SetupResponse,
    SetupStatusResponse,
)

__all__ = [
    # Setup
    "SetupRequest",
    "SetupResponse",
    "SetupStatusResponse",
    # Auth
    "LoginRequest",
    "LogoutResponse",
    "TokenResponse",
    "UserResponse",
    # Category
    "CategoryCreate",
    "CategoryResponse",
    "CategoryUpdate",
]
