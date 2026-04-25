"""
Categories router — CRUD for categories.

Endpoints:
  GET    /api/categories            → list (any authenticated user)
  GET    /api/categories/{id}       → get one
  POST   /api/categories            → create (owner/admin only)
  PUT    /api/categories/{id}       → update (owner/admin only)
  DELETE /api/categories/{id}       → archive (owner/admin only)
  POST   /api/categories/{id}/restore → un-archive (owner/admin only)

💡 CONCEPT: Read vs Write permissions
   GET endpoints use `CurrentUser` — any logged-in user can browse the
   shared catalog.

   Write endpoints (POST/PUT/DELETE) use `Depends(require_admin_or_owner)`
   — members can use existing categories but can't change the catalog.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import CurrentUser, DbSession, require_admin_or_owner
from app.models import User
from app.schemas.category import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
)
from app.services import category as category_service
from app.services.category import (
    CategoryNotFoundError,
    DuplicateCategoryError,
)

router = APIRouter(
    prefix="/api/categories",
    tags=["categories"],
)


# Type alias for "user must be owner or admin"
AdminOrOwner = Annotated[User, Depends(require_admin_or_owner)]


# ============================================================
# GET /api/categories
# ============================================================

@router.get("", response_model=list[CategoryResponse])
def list_categories(
    user: CurrentUser,
    db: DbSession,
    include_archived: Annotated[
        bool,
        Query(description="Include archived categories in the result."),
    ] = False,
) -> list[CategoryResponse]:
    """List all categories for the account.

    By default returns only active categories — pass `?include_archived=true`
    to also see archived ones (useful for the settings page).
    """
    categories = category_service.list_categories(
        db,
        account_id=user.account_id,
        include_archived=include_archived,
    )
    return [CategoryResponse.model_validate(c) for c in categories]


# ============================================================
# GET /api/categories/{id}
# ============================================================

@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(
    category_id: int,
    user: CurrentUser,
    db: DbSession,
) -> CategoryResponse:
    """Get a single category by ID."""
    try:
        category = category_service.get_category(
            db,
            account_id=user.account_id,
            category_id=category_id,
        )
    except CategoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return CategoryResponse.model_validate(category)


# ============================================================
# POST /api/categories
# ============================================================

@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    payload: CategoryCreate,
    admin: AdminOrOwner,
    db: DbSession,
) -> CategoryResponse:
    """Create a new custom category.

    Returns 409 Conflict if a category with the same name and type
    already exists.
    """
    try:
        category = category_service.create_category(
            db,
            account_id=admin.account_id,
            payload=payload,
        )
    except DuplicateCategoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return CategoryResponse.model_validate(category)


# ============================================================
# PUT /api/categories/{id}
# ============================================================

@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    admin: AdminOrOwner,
    db: DbSession,
) -> CategoryResponse:
    """Update an existing category.

    All fields are optional — send only what you want to change.
    Renaming to a name+type that already exists returns 409 Conflict.
    """
    try:
        category = category_service.update_category(
            db,
            account_id=admin.account_id,
            category_id=category_id,
            payload=payload,
        )
    except CategoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except DuplicateCategoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return CategoryResponse.model_validate(category)


# ============================================================
# DELETE /api/categories/{id}  (archive)
# ============================================================

@router.delete("/{category_id}", response_model=CategoryResponse)
def archive_category(
    category_id: int,
    admin: AdminOrOwner,
    db: DbSession,
) -> CategoryResponse:
    """Archive (soft-delete) a category.

    The category is hidden from new-transaction forms but kept in the DB
    so historical transactions retain their classification. Idempotent —
    archiving an already-archived category is a no-op.

    Use POST /api/categories/{id}/restore to un-archive.
    """
    try:
        category = category_service.archive_category(
            db,
            account_id=admin.account_id,
            category_id=category_id,
        )
    except CategoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return CategoryResponse.model_validate(category)


# ============================================================
# POST /api/categories/{id}/restore
# ============================================================

@router.post("/{category_id}/restore", response_model=CategoryResponse)
def restore_category(
    category_id: int,
    admin: AdminOrOwner,
    db: DbSession,
) -> CategoryResponse:
    """Restore a previously archived category."""
    try:
        category = category_service.restore_category(
            db,
            account_id=admin.account_id,
            category_id=category_id,
        )
    except CategoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return CategoryResponse.model_validate(category)
