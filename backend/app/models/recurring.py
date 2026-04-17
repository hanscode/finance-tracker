"""
RecurringRule and QuickTemplate models — automation for frequent transactions.

💡 CONCEPT: Two flavors of "recurring"
   RECURRING RULE (automatic)
   - "Create a $1,500 rent payment on the 1st of every month"
   - Background job runs daily, generates transactions when their time comes
   - User doesn't have to think about it — bills just appear

   QUICK TEMPLATE (manual, one-click)
   - "Coffee at Blue Bottle — $5.50 — Dining Out"
   - Not periodic. User clicks "Apply template" when the event actually happens
   - Skips repetitive form entry

   Both save time, but solve different problems.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin
from app.models.enums import BudgetBucket, RecurringFrequency, TransactionType

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.category import Category
    from app.models.transaction import Transaction


class RecurringRule(Base, TimestampMixin):
    """A rule that auto-generates transactions on a schedule.

    Examples:
      - Salary: biweekly, $2,500, category="Salary"
      - Rent: monthly on the 1st, $1,500, category="Rent/Mortgage"
      - Netflix: monthly on the 15th, $15.99, category="Subscriptions"
      - Car insurance: quarterly, $300, category="Insurance"

    💡 CONCEPT: `next_occurrence`
       Instead of computing the next date on the fly every time, we store it.
       A daily background job says:
           "Find all rules where next_occurrence <= today AND is_active = true"
       Then for each: create a transaction, advance next_occurrence by one cycle.
    """
    __tablename__ = "recurring_rules"

    id: Mapped[int] = mapped_column(primary_key=True)

    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # --- Transaction template fields ---
    # These describe what each generated transaction will look like
    type: Mapped[TransactionType] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    budget_bucket: Mapped[BudgetBucket | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # --- Schedule ---
    frequency: Mapped[RecurringFrequency] = mapped_column(String(20), nullable=False)

    # When the recurrence cycle starts
    start_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Optional cutoff (e.g., "subscription ends Dec 31")
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Date of the NEXT transaction to be generated.
    # Recalculated each time a transaction is auto-generated.
    next_occurrence: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Lets the user pause without deleting
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # --- Relationships ---
    account: Mapped[Account] = relationship(back_populates="recurring_rules")

    category: Mapped[Category] = relationship(back_populates="recurring_rules")

    # All transactions this rule has generated over time.
    # Useful for "show me all the times I've paid rent via this rule".
    generated_transactions: Mapped[list[Transaction]] = relationship(
        back_populates="recurring_rule",
    )

    def __repr__(self) -> str:
        return (
            f"<RecurringRule id={self.id} {self.frequency} "
            f"amount={self.amount} next={self.next_occurrence}>"
        )


class QuickTemplate(Base, TimestampMixin):
    """A saved transaction template for one-click entry.

    Unlike RecurringRule, these are NOT auto-generated. The user explicitly
    applies them when the real transaction happens.

    Examples:
      - "Coffee at Blue Bottle — $5.50 — Dining Out, want"
      - "Gas fill-up — $45.00 — Transportation, need"
      - "Uber home — $12.00 — Transportation, want"

    Flow:
      1. User creates template once in /recurring page
      2. Later, they open the "New Transaction" screen
      3. They pick the template → form is pre-filled → user just confirms
    """
    __tablename__ = "quick_templates"

    id: Mapped[int] = mapped_column(primary_key=True)

    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # A short name so the user can find the template in a list.
    # E.g., "Morning coffee", "Gas fillup"
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # --- Template fields (copied verbatim into the new Transaction on apply) ---
    type: Mapped[TransactionType] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    budget_bucket: Mapped[BudgetBucket | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # --- Relationships ---
    account: Mapped[Account] = relationship(back_populates="quick_templates")
    category: Mapped[Category] = relationship(back_populates="quick_templates")

    def __repr__(self) -> str:
        return f"<QuickTemplate id={self.id} name={self.name!r} amount={self.amount}>"
