"""
First-time setup service.

Handles the one-time account creation when the app is launched for the
first time. Also seeds default categories so new installs have something
to work with immediately.

💡 CONCEPT: Service layer
   This module knows NOTHING about HTTP. It accepts primitive inputs
   (email, password, etc.), does the database work, and returns objects.

   The HTTP router calls these functions after parsing the request. This
   way we could:
   - Call setup from a CLI script (no HTTP involved)
   - Call setup from tests (no HTTP involved)
   - Swap HTTP for gRPC later without changing business logic
"""

from sqlalchemy.orm import Session

from app import security
from app.models import (
    Account,
    AccountSettings,
    AuthMethod,
    BudgetBucket,
    Category,
    TransactionType,
    User,
    UserRole,
)

# ============================================================
# Default categories — seeded on account creation
# ============================================================
#
# Format: (name, type, budget_bucket, icon, color)
# Icons follow the `lucide-react` naming convention (what we'll use on the frontend).
#
# 💡 CONCEPT: Why seed data lives in code
#    Some apps put defaults in JSON/YAML files. We put them in Python
#    because:
#    - Type safety: the enums catch typos at import time
#    - Versionable: each default change shows up in git diff
#    - Tests can import the list directly
#    - Simple: no YAML parsers needed
DEFAULT_CATEGORIES: list[tuple[str, TransactionType, BudgetBucket | None, str, str]] = [
    # --- Income ---
    ("Salary",         TransactionType.INCOME,     None,                 "briefcase",      "#10b981"),
    ("Freelance",      TransactionType.INCOME,     None,                 "laptop",         "#14b8a6"),
    ("Other Income",   TransactionType.INCOME,     None,                 "trending-up",    "#06b6d4"),

    # --- Needs (essential expenses) ---
    ("Rent/Mortgage",  TransactionType.EXPENSE,    BudgetBucket.NEED,    "home",           "#ef4444"),
    ("Utilities",      TransactionType.EXPENSE,    BudgetBucket.NEED,    "zap",            "#f97316"),
    ("Groceries",      TransactionType.EXPENSE,    BudgetBucket.NEED,    "shopping-cart",  "#f59e0b"),
    ("Transportation", TransactionType.EXPENSE,    BudgetBucket.NEED,    "car",            "#eab308"),
    ("Insurance",      TransactionType.EXPENSE,    BudgetBucket.NEED,    "shield",         "#84cc16"),
    ("Healthcare",     TransactionType.EXPENSE,    BudgetBucket.NEED,    "heart-pulse",    "#ef4444"),
    ("Debt Payment",   TransactionType.EXPENSE,    BudgetBucket.NEED,    "credit-card",    "#dc2626"),
    ("Education",      TransactionType.EXPENSE,    BudgetBucket.NEED,    "book-open",      "#0ea5e9"),

    # --- Wants (discretionary) ---
    ("Dining Out",     TransactionType.EXPENSE,    BudgetBucket.WANT,    "utensils",       "#ec4899"),
    ("Entertainment",  TransactionType.EXPENSE,    BudgetBucket.WANT,    "clapperboard",   "#a855f7"),
    ("Shopping",       TransactionType.EXPENSE,    BudgetBucket.WANT,    "shopping-bag",   "#d946ef"),
    ("Subscriptions",  TransactionType.EXPENSE,    BudgetBucket.WANT,    "repeat",         "#8b5cf6"),
    ("Travel",         TransactionType.EXPENSE,    BudgetBucket.WANT,    "plane",          "#6366f1"),
    ("Personal Care",  TransactionType.EXPENSE,    BudgetBucket.WANT,    "sparkles",       "#f472b6"),

    # --- Savings ---
    ("Emergency Fund", TransactionType.SAVINGS,    BudgetBucket.SAVINGS, "life-buoy",      "#3b82f6"),
    ("Investments",    TransactionType.INVESTMENT, BudgetBucket.SAVINGS, "line-chart",     "#2563eb"),
    ("Donations",      TransactionType.DONATION,   BudgetBucket.WANT,    "heart",          "#f43f5e"),

    # --- Catch-all ---
    ("Other",          TransactionType.EXPENSE,    None,                 "more-horizontal", "#6b7280"),
]


# ============================================================
# Public API
# ============================================================

def is_setup_completed(db: Session) -> bool:
    """Check if the initial setup has been done.

    Returns True if an Account row exists with setup_completed = True.
    """
    account = db.query(Account).first()
    return account is not None and account.setup_completed


def get_account(db: Session) -> Account | None:
    """Return the (singleton) Account if it exists."""
    return db.query(Account).first()


def create_initial_account(
    db: Session,
    *,
    account_name: str,
    owner_email: str,
    owner_name: str,
    owner_password: str,
    currency: str = "USD",
) -> tuple[Account, User]:
    """Create the singleton Account + its Owner user + default categories.

    💡 CONCEPT: Keyword-only arguments (the `*` in the signature)
       The `*,` forces all following args to be passed by name.
       So callers must write:
           create_initial_account(db, owner_email="hans@...", ...)
       Not:
           create_initial_account(db, "hans@...", ...)

       This prevents mix-ups when arguments are all strings.

    Args:
        db: SQLAlchemy session
        account_name: Display name for the account
        owner_email: Email of the owner user
        owner_name: Display name of the owner
        owner_password: Plaintext password (will be hashed)
        currency: ISO 4217 currency code

    Returns:
        (Account, User) — the created account and its owner

    Raises:
        ValueError: if setup is already completed
    """
    # Guard: don't allow a second setup
    if is_setup_completed(db):
        raise ValueError("Setup has already been completed.")

    # Create the account
    account = Account(
        name=account_name,
        auth_method=AuthMethod.PASSWORD,
        setup_completed=True,
    )

    # Attach settings (via the relationship — cascade handles the insert)
    account.settings = AccountSettings(currency=currency)

    db.add(account)
    db.flush()  # Populate account.id without committing yet

    # Create the owner user
    owner = User(
        account_id=account.id,
        email=owner_email.lower(),     # normalize email for uniqueness
        name=owner_name,
        password_hash=security.hash_password(owner_password),
        role=UserRole.OWNER,
    )
    db.add(owner)

    # Seed default categories
    _seed_default_categories(db, account_id=account.id)

    # Commit the whole thing as one atomic transaction.
    # If anything fails, EVERYTHING rolls back (no half-setup state).
    db.commit()
    db.refresh(account)
    db.refresh(owner)

    return account, owner


# ============================================================
# Internal helpers
# ============================================================

def _seed_default_categories(db: Session, *, account_id: int) -> None:
    """Insert the default categories for a freshly created account.

    Prefixed with `_` to signal: "this is internal, don't call from outside".
    Python doesn't enforce privacy, but the convention is widely respected.
    """
    categories = [
        Category(
            account_id=account_id,
            name=name,
            type=type_,
            budget_bucket=bucket,
            icon=icon,
            color=color,
            is_default=True,
        )
        for name, type_, bucket, icon, color in DEFAULT_CATEGORIES
    ]
    db.add_all(categories)
    db.flush()
