"""
Pydantic schemas for authentication endpoints.

💡 CONCEPT: Input vs Output schemas
   We define SEPARATE classes for requests (input) and responses (output).
   Even if a response "looks like" the request, keeping them apart means
   we can evolve them independently. A classic example: adding a `role`
   field to the response without forcing clients to send it in requests.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole

# ============================================================
# POST /api/auth/login
# ============================================================

class LoginRequest(BaseModel):
    """Login payload (email + password).

    Pydantic's EmailStr does basic email syntax validation. Combined with
    the unique index on User.email, we get both input validation and
    database integrity.
    """
    email: EmailStr = Field(description="User's email address.")
    password: str = Field(
        min_length=1,   # don't leak exact min length on login
        max_length=72,
        description="Plaintext password. Verified against stored argon2id hash.",
    )


class TokenResponse(BaseModel):
    """Response after successful login.

    Follows the OAuth2 Bearer Token format loosely. That's why we include
    `token_type: "bearer"` — it tells clients to send the token as:

        Authorization: Bearer <access_token>
    """
    access_token: str = Field(description="JWT signed with the server's secret.")
    token_type: str = Field(default="bearer", description="Always 'bearer'.")
    expires_at: datetime = Field(description="When this token expires (UTC).")


# ============================================================
# GET /api/auth/me
# ============================================================

class UserResponse(BaseModel):
    """Info about the currently authenticated user.

    💡 CONCEPT: model_config = ConfigDict(from_attributes=True)
       This tells Pydantic it's OK to read fields from OBJECT ATTRIBUTES
       (like SQLAlchemy models), not just from dicts.

       Without it:
           user = db.query(User).first()
           UserResponse.model_validate(user)   # ← TypeError

       With it:
           UserResponse.model_validate(user)   # ← works, reads user.id, user.email, etc.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str
    role: UserRole
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime


# ============================================================
# POST /api/auth/logout
# ============================================================

class LogoutResponse(BaseModel):
    """Response after logout. Confirmation message only."""
    status: str = "ok"
    message: str = "Logged out successfully."
