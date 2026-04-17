"""
Category and Tag models — how transactions are classified.

💡 CONCEPT: Category vs Tag — why both?
   Categories and tags seem similar but serve different purposes:

   CATEGORY (one per transaction)
   - Primary classification: "Groceries", "Salary", "Rent"
   - Ties to budget buckets (need/want/savings)
   - Used for budgeting and reports
   - Drives the 50/30/20 engine

   TAG (many per transaction)
   - Flexible secondary labels: "vacation-2026", "tax-deductible", "shared-with-roommate"
   - User creates ad-hoc as needed
   - Used for cross-category grouping and search

   Example:
       Transaction: $800 flight to Tokyo
       Category: "Travel" (budget bucket: want)
       Tags: ["vacation-2026", "tax-deductible"]

💡 CONCEPT: Many-to-many via association table
   A transaction can have many tags, and a tag can be on many transactions.
   That's a classic many-to-many relationship, which requires a third "join"
   table. We define it as `transaction_tags` in transaction.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin
from app.models.enums import BudgetBucket, TransactionType

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.debt import Debt
    from app.models.goal import SavingsGoal
    from app.models.recurring import QuickTemplate, RecurringRule
    from app.models.transaction import Transaction


class Category(Base, TimestampMixin):
    """A classification for transactions.

    Examples: "Groceries", "Salary", "Rent/Mortgage", "Entertainment".
    Each category has a type (is it for income or expense?) and a budget
    bucket (need/want/savings) that drives the 50/30/20 engine.
    """
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)

    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Human-readable name shown in the UI
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # What kind of transaction this category applies to.
    # Examples:
    #   - "Salary"       → INCOME
    #   - "Groceries"    → EXPENSE
    #   - "Emergency"    → SAVINGS
    #   - "Stocks"       → INVESTMENT
    type: Mapped[TransactionType] = mapped_column(String(20), nullable=False)

    # 50/30/20 classification. Nullable for categories that don't fit the
    # model (e.g., income categories like "Salary" — income isn't budgeted,
    # it's the SOURCE of the budget).
    budget_bucket: Mapped[BudgetBucket | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # --- Visual identity ---
    # Icon name (e.g., "shopping-cart", "utensils"). We'll use lucide-react
    # on the frontend, so these are lucide icon names.
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Hex color code for charts and badges (e.g., "#ef4444")
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)

    # --- Flags ---
    # Was this seeded by the app (vs. created by the user)?
    # Useful to prevent users from deleting defaults, or to know which are
    # "system" categories.
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Soft delete: archived categories are hidden but kept in the DB so
    # historical transactions still reference a valid category.
    # 💡 CONCEPT: Why soft delete?
    #    If a user deletes "Entertainment" but has 50 past transactions
    #    categorized there, hard-deleting would orphan those transactions.
    #    Archiving keeps the data consistent while hiding it from new entries.
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # --- Relationships ---
    account: Mapped[Account] = relationship(back_populates="categories")

    transactions: Mapped[list[Transaction]] = relationship(
        back_populates="category",
    )

    recurring_rules: Mapped[list[RecurringRule]] = relationship(
        back_populates="category",
    )

    quick_templates: Mapped[list[QuickTemplate]] = relationship(
        back_populates="category",
    )

    savings_goals: Mapped[list[SavingsGoal]] = relationship(
        back_populates="category",
    )

    debts: Mapped[list[Debt]] = relationship(
        back_populates="category",
    )

    __table_args__ = (
        # Names must be unique per account (and per type).
        # This allows "Groceries" as both an expense and, theoretically,
        # a different category elsewhere. In practice, having duplicate
        # names across types would be confusing, but the schema allows it.
        UniqueConstraint("account_id", "name", "type", name="uq_categories_account_name_type"),
    )

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name!r} type={self.type}>"


class Tag(Base, TimestampMixin):
    """Flexible labels for cross-category grouping.

    Examples: "vacation-2026", "tax-deductible", "shared-expense".
    A transaction can have multiple tags. See `transaction_tags` in
    transaction.py for the many-to-many association table.
    """
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)

    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(50), nullable=False)

    # Optional color for visual distinction in the UI
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)

    # --- Relationships ---
    account: Mapped[Account] = relationship(back_populates="tags")

    # Many-to-many with Transaction — defined via `secondary` on the
    # Transaction side (cleaner to keep M2M declarations in one place).
    transactions: Mapped[list[Transaction]] = relationship(
        secondary="transaction_tags",
        back_populates="tags",
    )

    __table_args__ = (
        # Tag names must be unique per account
        UniqueConstraint("account_id", "name", name="uq_tags_account_name"),
    )

    def __repr__(self) -> str:
        return f"<Tag id={self.id} name={self.name!r}>"
