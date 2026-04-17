"""
SavingsGoal model — track progress toward a financial target.

Examples:
  - Emergency fund: $10,000 by no specific date
  - Vacation to Japan: $5,000 by 2026-11-01
  - Down payment: $50,000 by 2027-06-01

💡 CONCEPT: Goals vs Categories
   A goal is NOT a category. A goal is a target that you work toward using
   categories.

   Example flow:
     1. User creates goal "Vacation to Japan" — target $5,000 by Nov 1
     2. User links it to a category "Travel Savings"
     3. Every transaction in that category counts toward the goal
     4. Dashboard shows the progress bar computed from those transactions

   The `current_amount` is NOT stored — it's always derived from
   transactions. Storing it would make it go stale.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.category import Category


class SavingsGoal(Base, TimestampMixin):
    """A savings target with optional deadline."""
    __tablename__ = "savings_goals"

    id: Mapped[int] = mapped_column(primary_key=True)

    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Human-readable name ("Emergency fund", "Vacation to Japan")
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Optional description / notes about the goal
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # The target amount to save
    target_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Optional deadline. Used to compute "how much do I need to save per month?"
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Link to a category so transactions there count toward this goal.
    # Nullable because a user might not want to link yet.
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Visual customization
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)

    # Flag set manually by user when they consider the goal achieved
    # (or automatically when current >= target)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # --- Relationships ---
    account: Mapped[Account] = relationship(back_populates="savings_goals")
    category: Mapped[Category | None] = relationship(back_populates="savings_goals")

    def __repr__(self) -> str:
        return f"<SavingsGoal id={self.id} name={self.name!r} target={self.target_amount}>"
