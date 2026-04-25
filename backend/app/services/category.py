"""
Category service — business logic for category CRUD.

💡 CONCEPT: Service signatures
   Every function takes:
   - `db: Session`           — the open DB session (injected by the router)
   - `account_id: int`       — for scoping queries (injected from current_user)
   - `*, ...kwargs`          — actual data (keyword-only for safety)

   The service NEVER reads the current user from anywhere — it only knows
   what the caller passes. This makes it trivial to test (no FastAPI
   request context) and reusable (CLI, jobs, etc.).
"""

from sqlalchemy.orm import Session

from app.models import Category
from app.schemas.category import CategoryCreate, CategoryUpdate


class CategoryNotFoundError(Exception):
    """Raised when a category doesn't exist or doesn't belong to the account."""


class DuplicateCategoryError(Exception):
    """Raised when creating a category whose (name, type) already exists."""


# ============================================================
# Read operations
# ============================================================

def list_categories(
    db: Session,
    *,
    account_id: int,
    include_archived: bool = False,
) -> list[Category]:
    """List all categories for the account.

    By default excludes archived ones (since the UI usually shows only
    active categories). Pass `include_archived=True` for a settings page
    that wants to show everything.

    Returns categories ordered by `is_default DESC, name ASC` so the
    seeded ones appear first, then user-created in alphabetical order.
    """
    query = db.query(Category).filter(Category.account_id == account_id)

    if not include_archived:
        query = query.filter(Category.is_archived.is_(False))

    return query.order_by(Category.is_default.desc(), Category.name.asc()).all()


def get_category(
    db: Session,
    *,
    account_id: int,
    category_id: int,
) -> Category:
    """Fetch one category by ID — scoped to the account.

    💡 CONCEPT: Why filter by account_id even when querying by primary key?
       account_id is technically redundant (the PK alone uniquely identifies
       the row). But filtering by both makes the query "fail closed":
       even if a malicious user guessed an ID belonging to a different
       account (in a hypothetical multi-tenant deployment), they'd get
       a NotFound instead of a leak. Defense in depth.

    Raises:
        CategoryNotFoundError: if no category matches.
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
        raise CategoryNotFoundError(
            f"Category {category_id} not found in this account."
        )

    return category


# ============================================================
# Write operations
# ============================================================

def create_category(
    db: Session,
    *,
    account_id: int,
    payload: CategoryCreate,
) -> Category:
    """Create a new (custom) category.

    Enforces uniqueness on (account_id, name, type) — same constraint
    we declared on the DB. The DB would reject duplicates anyway, but
    we check first to return a friendly 409 instead of a generic 500.

    Raises:
        DuplicateCategoryError: if a category with the same name+type exists.
    """
    # Pre-flight check (covers both archived and active categories)
    existing = (
        db.query(Category)
        .filter(
            Category.account_id == account_id,
            Category.name == payload.name,
            Category.type == payload.type,
        )
        .first()
    )

    if existing is not None:
        raise DuplicateCategoryError(
            f"A {payload.type.value} category named '{payload.name}' already exists."
        )

    category = Category(
        account_id=account_id,
        name=payload.name,
        type=payload.type,
        budget_bucket=payload.budget_bucket,
        icon=payload.icon,
        color=payload.color,
        is_default=False,  # User-created → not a default
    )
    db.add(category)
    db.commit()
    db.refresh(category)

    return category


def update_category(
    db: Session,
    *,
    account_id: int,
    category_id: int,
    payload: CategoryUpdate,
) -> Category:
    """Update fields on an existing category.

    Only the fields the client sent are applied (PATCH semantics).
    Validates the (account_id, name, type) uniqueness if name or type
    changes.

    💡 CONCEPT: model_dump(exclude_unset=True)
       Pydantic provides this to get only the fields the client actually
       sent (vs. the defaults). It's the cleanest way to do PATCH:
           data = payload.model_dump(exclude_unset=True)
           for field, value in data.items():
               setattr(category, field, value)

    Raises:
        CategoryNotFoundError: if the category doesn't exist.
        DuplicateCategoryError: if renaming would conflict with another category.
    """
    category = get_category(db, account_id=account_id, category_id=category_id)

    updates = payload.model_dump(exclude_unset=True)

    # Check for duplicate if name or type would change
    new_name = updates.get("name", category.name)
    new_type = updates.get("type", category.type)
    if (new_name, new_type) != (category.name, category.type):
        conflict = (
            db.query(Category)
            .filter(
                Category.account_id == account_id,
                Category.name == new_name,
                Category.type == new_type,
                Category.id != category.id,
            )
            .first()
        )
        if conflict is not None:
            # `new_type` could be a TransactionType enum (from payload) or a
            # str (from the existing category). Normalize for the error message.
            type_str = new_type.value if hasattr(new_type, "value") else new_type
            raise DuplicateCategoryError(
                f"A {type_str} category named '{new_name}' already exists."
            )

    for field, value in updates.items():
        setattr(category, field, value)

    db.commit()
    db.refresh(category)
    return category


def archive_category(
    db: Session,
    *,
    account_id: int,
    category_id: int,
) -> Category:
    """Soft-delete a category by setting `is_archived=True`.

    💡 CONCEPT: Soft delete preserves data integrity
       If we hard-deleted a category that had transactions linked to it,
       the FK with ondelete=RESTRICT would block the delete. And even if
       it didn't, we'd lose historical context (a transaction would lose
       its category).

       Archiving keeps history intact while hiding the category from
       new-transaction forms.

    Idempotent: archiving an already-archived category is a no-op (still
    returns 200, not an error).
    """
    category = get_category(db, account_id=account_id, category_id=category_id)

    if not category.is_archived:
        category.is_archived = True
        db.commit()
        db.refresh(category)

    return category


def restore_category(
    db: Session,
    *,
    account_id: int,
    category_id: int,
) -> Category:
    """Un-archive a category."""
    category = get_category(db, account_id=account_id, category_id=category_id)

    if category.is_archived:
        category.is_archived = False
        db.commit()
        db.refresh(category)

    return category
