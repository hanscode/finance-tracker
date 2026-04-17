"""
User, Session, and MagicLinkToken models — everything related to authentication.

💡 CONCEPT: Why three models?
   - User: who you are (identity + permissions)
   - Session: proof you've logged in (long-lived, for API requests)
   - MagicLinkToken: short-lived one-time token for passwordless login

   Separating them keeps each model focused. Sessions and magic links have
   very different lifecycles (days vs 15 minutes, reusable vs single-use),
   so mixing them in one table would be messy.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.transaction import Transaction


class User(Base, TimestampMixin):
    """A person who can log into the account.

    💡 CONCEPT: Nullable password_hash
       Why is `password_hash` nullable? Because if the admin configured
       magic link auth, users never set a password. The field stays NULL
       until/unless they switch to password auth.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Every user belongs to the one account
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Email is the login identifier. Case-insensitive in practice (we lowercase
    # before storing), so `john@` and `JOHN@` are the same user.
    email: Mapped[str] = mapped_column(String(255), nullable=False)

    # Display name shown in the UI
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # bcrypt hash. Nullable because magic-link-only users never set a password.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Permission level
    role: Mapped[UserRole] = mapped_column(
        String(20),
        default=UserRole.MEMBER,
        nullable=False,
    )

    # Soft disable: keeps the user's history but prevents login
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Track last successful login (useful for UI + "account inactive" detection)
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # --- Relationships ---
    account: Mapped[Account] = relationship(back_populates="users")

    sessions: Mapped[list[Session]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    magic_link_tokens: Mapped[list[MagicLinkToken]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # Transactions the user created (via the `created_by` FK on Transaction)
    created_transactions: Mapped[list[Transaction]] = relationship(
        back_populates="creator",
        foreign_keys="Transaction.created_by",
    )

    __table_args__ = (
        # Email must be unique PER ACCOUNT (composite unique).
        # In theory we could just do `email` unique globally since there's
        # only one account, but this is cleaner semantically.
        UniqueConstraint("account_id", "email", name="uq_users_account_email"),

        # Fast lookup on email (for login)
        Index("ix_users_email", "email"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role}>"


class Session(Base, TimestampMixin):
    """Tracks an active login session.

    💡 CONCEPT: Why track sessions in the DB?
       JWTs are stateless — they don't need a DB. So why bother?

       Because we want features like:
       - "Log out from all devices"
       - "See your active sessions in settings"
       - Instant revocation (a stolen JWT stays valid until it expires,
         unless we check a revocation list)

       Each issued JWT has a corresponding row here. On each request, we
       verify the row exists and hasn't been revoked.

    💡 CONCEPT: Why store `token_hash` instead of the raw token?
       If the DB leaks, raw tokens = attacker takes over every active session.
       Storing only the hash makes leaked data useless for impersonation.
    """
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # SHA-256 hash of the session token (the raw token is only sent to the client)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    # Device info for the UI ("You're logged in from Chrome on macOS")
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)  # IPv6 fits in 45

    # When the session expires (typically 30 days from creation)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Refreshed on activity to support "idle timeout"
    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # --- Relationship ---
    user: Mapped[User] = relationship(back_populates="sessions")

    def __repr__(self) -> str:
        return f"<Session id={self.id} user_id={self.user_id} expires_at={self.expires_at}>"


class MagicLinkToken(Base, TimestampMixin):
    """Short-lived, single-use token for passwordless email login.

    💡 CONCEPT: Single-use tokens
       Unlike sessions, magic link tokens are consumed on first use. We mark
       them used by setting `used_at` — never delete, so we have an audit
       trail.

       Flow:
       1. User enters email → POST /api/auth/magic-link
       2. We generate a random token, hash it, store a MagicLinkToken row,
          email the raw token as a URL
       3. User clicks link → POST /api/auth/magic-link/verify with the token
       4. We hash the incoming token, look up the row, check:
          - Not expired
          - Not already used
       5. Mark used, issue a session JWT
    """
    __tablename__ = "magic_link_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Hash of the raw token (same reasoning as Session.token_hash)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    # 15 minutes from creation (enforced in application logic)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # When was this token redeemed? Null = unused. Set = already used, can't reuse.
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # --- Relationship ---
    user: Mapped[User] = relationship(back_populates="magic_link_tokens")

    __table_args__ = (
        # Speed up the "find my valid unused token" query
        Index("ix_magic_link_tokens_user_used", "user_id", "used_at"),
    )

    def __repr__(self) -> str:
        return f"<MagicLinkToken id={self.id} user_id={self.user_id} used={self.used_at is not None}>"
