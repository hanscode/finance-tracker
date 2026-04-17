"""
Shared enumerations used across the data model.

💡 CONCEPT: Why Enums instead of strings?
   In the Techdegree you probably used strings like "income" or "expense"
   directly. That works but has problems:

   1. Typos: "incmoe" silently creates invalid data
   2. No autocomplete: you have to remember every valid value
   3. No refactoring: renaming "income" → "earning" means find-and-replace
      across the whole codebase

   Enums solve all three. They define a closed set of valid values that
   Python + SQLAlchemy enforce at runtime.

💡 CONCEPT: str + Enum (inheriting from both)
   We inherit from both `str` and `Enum`. This means:
   - UserRole.OWNER == "owner" → True (behaves like a string)
   - Serializes cleanly to JSON (FastAPI handles this automatically)
   - SQLAlchemy stores the string value in the database
"""

from enum import Enum


class UserRole(str, Enum):
    """Who can do what in the account."""
    OWNER = "owner"      # The person who installed the app
    ADMIN = "admin"      # Trusted member with near-full access
    MEMBER = "member"    # Can add/view transactions but not change settings


class AuthMethod(str, Enum):
    """How users authenticate on this installation."""
    MAGIC_LINK = "magic_link"  # Email-based, no password (requires SMTP)
    PASSWORD = "password"      # Traditional email + password


class TransactionType(str, Enum):
    """What kind of financial movement a transaction represents."""
    INCOME = "income"           # Money coming in (salary, freelance)
    EXPENSE = "expense"         # Money going out (groceries, rent)
    TRANSFER = "transfer"       # Moving money between own accounts
    SAVINGS = "savings"         # Setting money aside for future goals
    INVESTMENT = "investment"   # Money put into assets (stocks, crypto)
    DONATION = "donation"       # Charitable giving


class BudgetBucket(str, Enum):
    """50/30/20 budgeting classification.

    Every expense belongs to one of these three buckets.
    The budget engine uses these to track spending vs. income.
    """
    NEED = "need"        # Essential: rent, utilities, groceries, insurance
    WANT = "want"        # Discretionary: dining out, entertainment, travel
    SAVINGS = "savings"  # Future self: emergency fund, investments, debt payoff


class RecurringFrequency(str, Enum):
    """How often a recurring transaction is generated."""
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"      # Every 2 weeks (common for paychecks)
    MONTHLY = "monthly"         # Most common for bills
    QUARTERLY = "quarterly"     # Every 3 months (some insurance, taxes)
    YEARLY = "yearly"           # Annual subscriptions, property tax


class ThemeMode(str, Enum):
    """UI theme preference."""
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"  # Follow the user's OS preference


class DateFormat(str, Enum):
    """How dates are displayed across the UI."""
    US = "MM/DD/YYYY"        # 04/16/2026 (American)
    EU = "DD/MM/YYYY"        # 16/04/2026 (European / most of the world)
    ISO = "YYYY-MM-DD"       # 2026-04-16 (international standard)


class DayOfWeek(str, Enum):
    """First day of the week (for calendar views and weekly reports)."""
    SUNDAY = "sunday"
    MONDAY = "monday"
