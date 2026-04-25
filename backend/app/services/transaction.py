"""
Transaction service — list with filters/pagination, CRUD, tag handling.

The most consequential service in the app. Performance and correctness
here directly affect every dashboard, report, and budget calculation
later on.
"""

import datetime as dt
import math
from decimal import Decimal

from sqlalchemy.orm import Session, selectinload

from app.models import Category, Tag, Transaction, User
from app.models.enums import BudgetBucket, TransactionType
from app.schemas.transaction import TransactionCreate, TransactionUpdate

# ============================================================
# Custom exceptions
# ============================================================

class TransactionNotFoundError(Exception):
    """Raised when a transaction doesn't exist or doesn't belong to the account."""


class CategoryInvalidError(Exception):
    """Raised when the referenced category doesn't exist, is archived, or
    belongs to a different account."""


# ============================================================
# Helpers
# ============================================================

def _validate_category(db: Session, *, account_id: int, category_id: int) -> Category:
    """Make sure the category exists, belongs to this account, and is not archived.

    💡 CONCEPT: Validate FKs in the service, not just in the DB
       The DB will reject a bad FK with IntegrityError, but that:
       1. Triggers a 500 instead of 4xx
       2. Doesn't tell the client WHY (vs. "category is archived")

       Validating here lets us return 409 Conflict with a clear message.
    """
    category = (
        db.query(Category)
        .filter(
            Category.id == category_id,
            Category.account_id == account_id,
        )
        .first()
    )
    if category is None:
        raise CategoryInvalidError(f"Category {category_id} not found in this account.")
    if category.is_archived:
        raise CategoryInvalidError(
            f"Category '{category.name}' is archived. Restore it first or pick another."
        )
    return category


def _ensure_tags(db: Session, *, account_id: int, tag_names: list[str]) -> list[Tag]:
    """Find existing tags by name, create missing ones, return the full list.

    Tag names are normalized (stripped, lowercased) so 'Vacation' and
    ' vacation ' both map to 'vacation'.

    💡 CONCEPT: Bulk-fetch then create-missing
       Naive approach: loop, query each name. With 5 tags = 5 queries.

       Better: ONE query for all names, set-difference for missing,
       INSERT in batch. With 5 tags = 2 queries.
    """
    if not tag_names:
        return []

    # Normalize and de-duplicate
    cleaned = sorted({name.strip().lower() for name in tag_names if name.strip()})

    # One query: find all that already exist
    existing = (
        db.query(Tag)
        .filter(Tag.account_id == account_id, Tag.name.in_(cleaned))
        .all()
    )
    existing_by_name = {tag.name: tag for tag in existing}

    # Create the missing ones
    result = []
    for name in cleaned:
        tag = existing_by_name.get(name)
        if tag is None:
            tag = Tag(account_id=account_id, name=name)
            db.add(tag)
        result.append(tag)

    db.flush()  # Make sure new tag IDs are populated before returning
    return result


# ============================================================
# Read operations
# ============================================================

def list_transactions(
    db: Session,
    *,
    account_id: int,
    # Filters
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    type: TransactionType | None = None,
    category_id: int | None = None,
    budget_bucket: BudgetBucket | None = None,
    search: str | None = None,
    tags: list[str] | None = None,
    # Pagination
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[Transaction], int]:
    """List transactions with optional filters and pagination.

    Returns (items, total) — `total` is the count BEFORE pagination,
    so the caller can compute total_pages.

    💡 CONCEPT: selectinload for eager loading
       Without `selectinload`, accessing `transaction.tags` for each row
       fires a separate query (the N+1 problem). With it, SQLAlchemy
       batches them into a single IN-clause query.

       Same for `transaction.creator`.
    """
    query = (
        db.query(Transaction)
        .options(
            selectinload(Transaction.tags),
            selectinload(Transaction.creator),
        )
        .filter(Transaction.account_id == account_id)
    )

    # Apply filters one by one
    if date_from is not None:
        query = query.filter(Transaction.date >= date_from)
    if date_to is not None:
        query = query.filter(Transaction.date <= date_to)
    if type is not None:
        query = query.filter(Transaction.type == type)
    if category_id is not None:
        query = query.filter(Transaction.category_id == category_id)
    if budget_bucket is not None:
        query = query.filter(Transaction.budget_bucket == budget_bucket)

    if search:
        # Case-insensitive partial match on description.
        # SQLite's LIKE is case-insensitive by default for ASCII.
        query = query.filter(Transaction.description.ilike(f"%{search}%"))

    if tags:
        # Match transactions that have ANY of the given tag names.
        # (Use AND/all-of by checking len(intersect) instead — choose UX-wise.)
        cleaned = [t.strip().lower() for t in tags if t.strip()]
        if cleaned:
            query = query.join(Transaction.tags).filter(Tag.name.in_(cleaned)).distinct()

    # Count BEFORE applying offset/limit
    total = query.count()

    # Order by most recent first (date DESC, then id DESC for tie-breaking)
    query = query.order_by(Transaction.date.desc(), Transaction.id.desc())

    # Pagination
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    return items, total


def get_transaction(
    db: Session,
    *,
    account_id: int,
    transaction_id: int,
) -> Transaction:
    """Fetch one transaction (with tags + creator eagerly loaded)."""
    transaction = (
        db.query(Transaction)
        .options(
            selectinload(Transaction.tags),
            selectinload(Transaction.creator),
        )
        .filter(
            Transaction.id == transaction_id,
            Transaction.account_id == account_id,
        )
        .first()
    )
    if transaction is None:
        raise TransactionNotFoundError(
            f"Transaction {transaction_id} not found in this account."
        )
    return transaction


# ============================================================
# Write operations
# ============================================================

def create_transaction(
    db: Session,
    *,
    account_id: int,
    creator: User,
    payload: TransactionCreate,
) -> Transaction:
    """Create a new transaction.

    - Validates the referenced category (exists, not archived, same account)
    - Auto-creates tags that don't exist yet
    - Defaults `budget_bucket` to the category's bucket if not specified
    - Sets `created_by` to the current user
    """
    category = _validate_category(db, account_id=account_id, category_id=payload.category_id)

    # If the client didn't override the bucket, inherit from the category
    bucket = payload.budget_bucket if payload.budget_bucket is not None else category.budget_bucket

    transaction = Transaction(
        account_id=account_id,
        created_by=creator.id,
        category_id=payload.category_id,
        type=payload.type,
        amount=payload.amount,
        date=payload.date,
        description=payload.description,
        budget_bucket=bucket,
        recurring_rule_id=None,        # set by the recurring-rule worker, not here
    )

    # Tags (creates missing ones automatically)
    if payload.tags:
        transaction.tags = _ensure_tags(
            db, account_id=account_id, tag_names=payload.tags
        )

    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return transaction


def update_transaction(
    db: Session,
    *,
    account_id: int,
    transaction_id: int,
    payload: TransactionUpdate,
) -> Transaction:
    """Apply a partial update to a transaction (PATCH semantics).

    Only the fields the client sent are touched. Tags are special:
    - If `tags` is omitted: leave them alone
    - If `tags=[]`: clear all tags
    - If `tags=["a","b"]`: replace with exactly those
    """
    transaction = get_transaction(
        db, account_id=account_id, transaction_id=transaction_id
    )

    updates = payload.model_dump(exclude_unset=True)

    # Validate category change before mutating
    if "category_id" in updates:
        _validate_category(db, account_id=account_id, category_id=updates["category_id"])

    # Tags need special handling — pop them out of `updates`
    new_tags = updates.pop("tags", None)

    # Apply scalar fields
    for field, value in updates.items():
        setattr(transaction, field, value)

    # Replace tags if requested
    if new_tags is not None:
        transaction.tags = _ensure_tags(db, account_id=account_id, tag_names=new_tags)

    db.commit()
    db.refresh(transaction)
    return transaction


def delete_transaction(
    db: Session,
    *,
    account_id: int,
    transaction_id: int,
) -> None:
    """Permanently delete a transaction.

    Unlike categories (which are soft-deleted), transactions are hard-
    deleted because they are leaves in the data graph — nothing else
    references them.

    💡 CONCEPT: Cleaning up orphan tags?
       We don't. A tag with zero transactions is harmless and cheap.
       If the user wants to tidy up, they can do it from the (future)
       /api/tags endpoint. Premature cleanup adds complexity for no gain.
    """
    transaction = get_transaction(
        db, account_id=account_id, transaction_id=transaction_id
    )
    db.delete(transaction)
    db.commit()


# ============================================================
# Pagination math (small helper, kept here so routers stay thin)
# ============================================================

def total_pages(total: int, per_page: int) -> int:
    """Number of pages needed to fit `total` items at `per_page` each."""
    if total == 0:
        return 0
    return math.ceil(total / per_page)


# Keep types-as-callable consistent with the rest of the codebase
# (so we don't have to import Decimal explicitly in routers).
__all__ = [
    "TransactionNotFoundError",
    "CategoryInvalidError",
    "list_transactions",
    "get_transaction",
    "create_transaction",
    "update_transaction",
    "delete_transaction",
    "total_pages",
    "Decimal",  # re-export for convenience
]
