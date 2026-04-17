"""
Transaction model — the fundamental unit of the finance tracker.

Every financial movement is a transaction. All budgeting, reporting, and
dashboards are built on top of this table.

💡 CONCEPT: Money handling — Decimal, not float
   We use SQLAlchemy's `Numeric(12, 2)` type, which maps to Python's `Decimal`.
   This gives us:
   - 12 total digits (up to 9,999,999,999.99)
   - 2 decimal places (standard for currency)
   - ZERO floating-point rounding errors

   If we used `Float`, $0.10 + $0.20 could end up as $0.30000000000000004.
   In accounting, that's unacceptable.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Column,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin
from app.models.enums import BudgetBucket, TransactionType

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.category import Category, Tag
    from app.models.recurring import RecurringRule
    from app.models.user import User


# ============================================
# Association table: Transaction ↔ Tag (many-to-many)
# ============================================
#
# 💡 CONCEPT: Association tables
#    A many-to-many relationship needs a third table that stores the pairings.
#    Each row here means "transaction X is tagged with tag Y".
#
#    We declare this as a `Table` (not a full model class) because there's no
#    extra data on the association itself — just the two foreign keys.
#
#    Example rows:
#      | transaction_id | tag_id |
#      |----------------|--------|
#      |       15       |   3    |   ← transaction 15 has tag 3
#      |       15       |   7    |   ← transaction 15 also has tag 7
#      |       22       |   3    |   ← transaction 22 has tag 3
transaction_tags = Table(
    "transaction_tags",
    Base.metadata,
    Column(
        "transaction_id",
        Integer,
        ForeignKey("transactions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        Integer,
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


# ============================================
# Transaction model
# ============================================
class Transaction(Base, TimestampMixin):
    """A single financial movement.

    Examples:
    - Salary deposit: type=income, amount=5000.00, category="Salary"
    - Grocery run: type=expense, amount=127.43, category="Groceries", bucket=need
    - Stock purchase: type=investment, amount=500.00, category="Stocks", bucket=savings
    """
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)

    # --- Ownership & authorship ---
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Who created this transaction (for accountability in multi-member accounts).
    # We use SET NULL on delete so that if a user is removed, their historical
    # transactions aren't deleted — they just lose the attribution.
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # --- Classification ---
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),
        # RESTRICT: you can't delete a category that has transactions.
        # User should archive the category instead.
        nullable=False,
        index=True,
    )

    # Redundant with category.type but denormalized for:
    # 1. Fast filtering (WHERE type = 'expense' without a JOIN)
    # 2. Historical integrity (even if the category changes, the transaction's
    #    type is locked in)
    type: Mapped[TransactionType] = mapped_column(String(20), nullable=False, index=True)

    # Same reasoning — denormalized from category.budget_bucket for performance
    # and historical accuracy. Nullable for income (income isn't "bucketed").
    budget_bucket: Mapped[BudgetBucket | None] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )

    # --- Financial data ---
    # Always stored as POSITIVE. The `type` field tells us if it's a +/- flow.
    # This prevents bugs where someone accidentally enters a negative income.
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # When the transaction actually occurred (not when it was entered).
    # Indexed because date-range queries are EXTREMELY common:
    #   "show me this month's expenses" → WHERE date >= '2026-04-01' AND date <= '2026-04-30'
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Free-form description (e.g., "Coffee at Blue Bottle", "Monthly gym fee")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Recurrence tracking ---
    # If this transaction was auto-generated by a RecurringRule, we link it here.
    # Helpful for:
    #   - Showing "this is a recurring transaction" badge in the UI
    #   - Letting the user edit/delete all future occurrences
    recurring_rule_id: Mapped[int | None] = mapped_column(
        ForeignKey("recurring_rules.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # --- Relationships ---
    account: Mapped[Account] = relationship(back_populates="transactions")

    creator: Mapped[User | None] = relationship(
        back_populates="created_transactions",
        foreign_keys=[created_by],
    )

    category: Mapped[Category] = relationship(back_populates="transactions")

    recurring_rule: Mapped[RecurringRule | None] = relationship(
        back_populates="generated_transactions",
    )

    # Many-to-many via the association table defined above
    tags: Mapped[list[Tag]] = relationship(
        secondary=transaction_tags,
        back_populates="transactions",
    )

    __table_args__ = (
        # Composite index for the most common query pattern:
        # "show me all transactions for this account in this date range"
        Index("ix_transactions_account_date", "account_id", "date"),

        # Another common query: spending breakdown by category for a period
        Index("ix_transactions_account_category_date", "account_id", "category_id", "date"),
    )

    def __repr__(self) -> str:
        return (
            f"<Transaction id={self.id} type={self.type} "
            f"amount={self.amount} date={self.date}>"
        )
