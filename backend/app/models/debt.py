"""
Debt model — track loans, credit cards, mortgages.

Examples:
  - Student loan: $25,000 at 5.5% APR, $300/month minimum
  - Credit card: $3,500 at 21.99% APR, $50/month minimum
  - Car loan: $18,000 at 4.2% APR, $450/month minimum

💡 CONCEPT: Debt tracking is about progress, not the debt itself
   We don't try to replace your bank's statements. We track:
   - Original amount (for showing "X% paid off" progress)
   - Interest rate (for projecting payoff date)
   - Minimum payment (for budgeting)

   Actual balance is derived from linked transactions (payments made).
   Keeps the model simple and truthful.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.category import Category


class Debt(Base, TimestampMixin):
    """A debt the user is paying off."""
    __tablename__ = "debts"

    id: Mapped[int] = mapped_column(primary_key=True)

    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Human-readable name ("Student loan", "Chase Freedom card")
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Optional extra notes (terms, lender, account number last 4 digits, etc.)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Debt amount when the user started tracking it.
    # Not necessarily the original loan amount — could be "balance as of today"
    # when adding an existing debt.
    original_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # APR as a percentage (e.g., 5.5 means 5.5%).
    # Using Numeric(5, 2) means max 999.99% (plenty for any legal rate).
    interest_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )

    # Monthly minimum payment (for budget forecasting)
    minimum_payment: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    # Link to a category so payments in that category count against this debt.
    # E.g., category "Student Loan Payment" → debt "Student loan"
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # --- Relationships ---
    account: Mapped[Account] = relationship(back_populates="debts")
    category: Mapped[Category | None] = relationship(back_populates="debts")

    def __repr__(self) -> str:
        return f"<Debt id={self.id} name={self.name!r} original={self.original_amount}>"
