"""
Pydantic schemas for the first-time setup wizard.

💡 CONCEPT: Pydantic vs SQLAlchemy models
   SQLAlchemy models map to DB tables. Pydantic schemas map to JSON
   payloads in HTTP requests/responses. They're similar but serve
   different purposes:

   - SQLAlchemy: `User.password_hash` (long bcrypt hash)
   - Pydantic:   `SetupRequest.owner_password` (plaintext, will be hashed)

   By keeping them separate, the API's public contract is decoupled from
   the database schema. We can change one without breaking the other.
"""

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import AuthMethod

# ============================================================
# GET /api/setup/status
# ============================================================

class SetupStatusResponse(BaseModel):
    """Response for checking whether the app has been set up yet."""

    setup_completed: bool = Field(
        description="Whether the initial setup has been completed."
    )
    auth_method: AuthMethod | None = Field(
        default=None,
        description="Auth method configured during setup (null if not set up).",
    )


# ============================================================
# POST /api/setup
# ============================================================

class SetupRequest(BaseModel):
    """Payload for the first-time setup wizard.

    Called exactly once, when the app is first launched. After completion,
    this endpoint returns 409 Conflict if called again.
    """

    # --- Account ---
    account_name: str = Field(
        min_length=1,
        max_length=100,
        description="Human-readable name for this installation (e.g., 'Hans Family').",
    )

    # --- Owner user ---
    owner_email: EmailStr = Field(
        description="Email address of the owner (first user).",
    )

    owner_name: str = Field(
        min_length=1,
        max_length=100,
        description="Display name of the owner.",
    )

    owner_password: str = Field(
        # bcrypt has a 72-byte limit; we cap at 72 chars to be safe
        # (in ASCII, 1 char = 1 byte).
        min_length=8,
        max_length=72,
        description="Plaintext password. Will be hashed with argon2id before storage.",
    )

    # --- Preferences (optional, sensible defaults) ---
    currency: str = Field(
        default="USD",
        min_length=3,
        max_length=3,
        pattern=r"^[A-Z]{3}$",  # ISO 4217 codes: USD, EUR, MXN, etc.
        description="Default currency (ISO 4217 code).",
    )


class SetupResponse(BaseModel):
    """Response after successful setup."""

    status: str = "ok"
    message: str = "Setup completed successfully. You can now log in."
