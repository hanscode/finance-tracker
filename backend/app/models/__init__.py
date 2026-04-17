"""
Models package — exposes all SQLAlchemy models.

💡 CONCEPT: Why re-export everything here?
   Two reasons:

   1. Convenience: users can `from app.models import User, Account` instead
      of `from app.models.user import User; from app.models.account import Account`.

   2. Alembic discovery: when Alembic introspects `Base.metadata` to detect
      schema changes, it only sees models that have been IMPORTED somewhere.
      If no module ever imports `Debt`, Alembic won't know it exists.

      Importing everything here ensures all models are registered when the
      package is loaded.
"""

from app.models.account import Account, AccountSettings
from app.models.base import TimestampMixin, utcnow
from app.models.category import Category, Tag
from app.models.debt import Debt
from app.models.enums import (
    AuthMethod,
    BudgetBucket,
    DateFormat,
    DayOfWeek,
    RecurringFrequency,
    ThemeMode,
    TransactionType,
    UserRole,
)
from app.models.goal import SavingsGoal
from app.models.recurring import QuickTemplate, RecurringRule
from app.models.transaction import Transaction, transaction_tags
from app.models.user import MagicLinkToken, Session, User

# Controls what gets imported with `from app.models import *`
# (rarely used, but good practice to declare)
__all__ = [
    # Base utilities
    "TimestampMixin",
    "utcnow",
    # Enums
    "AuthMethod",
    "BudgetBucket",
    "DateFormat",
    "DayOfWeek",
    "RecurringFrequency",
    "ThemeMode",
    "TransactionType",
    "UserRole",
    # Models
    "Account",
    "AccountSettings",
    "Category",
    "Debt",
    "MagicLinkToken",
    "QuickTemplate",
    "RecurringRule",
    "SavingsGoal",
    "Session",
    "Tag",
    "Transaction",
    "User",
    # Association tables
    "transaction_tags",
]
