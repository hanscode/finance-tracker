"""
Account model — the singleton root of the entire application.

One installation = one account = one shared financial life.

💡 CONCEPT: Why a singleton Account?
   Finance Tracker follows the ONCE philosophy (37signals): every installation
   is a single-tenant instance. There is no public user registration — the
   owner sets up the account on first launch, and all data (transactions,
   categories, goals, etc.) belongs to that one account.

   This is the same pattern Campfire and Writebook use. It enforces the
   "one installation per household" model at the database level.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin
from app.models.enums import AuthMethod, DateFormat, DayOfWeek, ThemeMode

# TYPE_CHECKING is a trick to avoid circular imports.
# At runtime, these imports are NOT executed (TYPE_CHECKING is always False).
# At type-check time (IDE, mypy), they ARE, giving us autocomplete + type safety.
if TYPE_CHECKING:
    from app.models.category import Category, Tag
    from app.models.debt import Debt
    from app.models.goal import SavingsGoal
    from app.models.recurring import QuickTemplate, RecurringRule
    from app.models.transaction import Transaction
    from app.models.user import User


class Account(Base, TimestampMixin):
    """The singleton account — one per installation.

    💡 CONCEPT: Singleton enforcement via UNIQUE constraint
       The `singleton_guard` column always has the value `True`. Because the
       column has a UNIQUE constraint, attempting to insert a second row
       will raise an IntegrityError at the database level.

       This is the 37signals pattern used in Campfire/Writebook.
    """
    __tablename__ = "accounts"

    # Standard primary key
    id: Mapped[int] = mapped_column(primary_key=True)

    # Display name for the account (e.g., "The Smith Family", "My Finances")
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Has the setup wizard been completed? Used to gate access to the app.
    setup_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Which auth method is active (magic_link requires SMTP, password doesn't)
    auth_method: Mapped[AuthMethod] = mapped_column(
        String(20),
        default=AuthMethod.PASSWORD,
        nullable=False,
    )

    # --- SMTP configuration (optional, for magic link auth) ---
    smtp_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    smtp_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    smtp_user: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # NOTE: In production we should encrypt this at rest. For now, stored
    # as-is. We'll add encryption in a later phase when we wire up magic links.
    smtp_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    smtp_from_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # --- Singleton guard ---
    # Always True. The UNIQUE constraint below ensures only one row can exist.
    singleton_guard: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # --- Relationships ---
    # `back_populates` creates a two-way link: if User has `account = relationship(..., back_populates="users")`,
    # and Account has `users = relationship(..., back_populates="account")`, then:
    #   user.account  → returns the Account
    #   account.users → returns a list of Users
    users: Mapped[list[User]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",  # Delete users if account is deleted
    )

    settings: Mapped[AccountSettings | None] = relationship(
        back_populates="account",
        uselist=False,  # one-to-one (not a list)
        cascade="all, delete-orphan",
    )

    categories: Mapped[list[Category]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
    )

    tags: Mapped[list[Tag]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
    )

    transactions: Mapped[list[Transaction]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
    )

    recurring_rules: Mapped[list[RecurringRule]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
    )

    quick_templates: Mapped[list[QuickTemplate]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
    )

    savings_goals: Mapped[list[SavingsGoal]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
    )

    debts: Mapped[list[Debt]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
    )

    # Enforce the singleton constraint at the database level
    __table_args__ = (
        UniqueConstraint("singleton_guard", name="uq_accounts_singleton"),
    )

    def __repr__(self) -> str:
        return f"<Account id={self.id} name={self.name!r}>"


class AccountSettings(Base, TimestampMixin):
    """User-facing preferences for the account.

    Shared across all members — everyone sees the same theme, currency, etc.

    💡 CONCEPT: One-to-one relationship via UNIQUE foreign key
       Normally a foreign key means many-to-one (many transactions → one
       account). To make it one-to-one, we add `unique=True` on the FK
       column, so only one settings row can point to a given account.
    """
    __tablename__ = "account_settings"

    id: Mapped[int] = mapped_column(primary_key=True)

    # unique=True turns this from many-to-one into one-to-one
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # --- Appearance ---
    theme: Mapped[ThemeMode] = mapped_column(
        String(10),
        default=ThemeMode.SYSTEM,
        nullable=False,
    )

    # --- Regional ---
    currency: Mapped[str] = mapped_column(
        String(3),               # ISO 4217 code: USD, EUR, MXN, etc.
        default="USD",
        nullable=False,
    )

    date_format: Mapped[DateFormat] = mapped_column(
        String(10),
        default=DateFormat.US,
        nullable=False,
    )

    first_day_of_week: Mapped[DayOfWeek] = mapped_column(
        String(10),
        default=DayOfWeek.SUNDAY,
        nullable=False,
    )

    # --- Budget (50/30/20 rule) ---
    # Optional: if not set, the app calculates net income from income transactions
    monthly_income: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),          # Up to 9,999,999,999.99 — plenty for any income
        nullable=True,
    )

    # Budget split percentages (must sum to 100 — enforced in application logic)
    budget_needs_pct: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    budget_wants_pct: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    budget_savings_pct: Mapped[int] = mapped_column(Integer, default=20, nullable=False)

    # --- Relationship back to Account ---
    account: Mapped[Account] = relationship(back_populates="settings")

    def __repr__(self) -> str:
        return f"<AccountSettings account_id={self.account_id} currency={self.currency}>"
