"""
Transactions router — CRUD endpoints for the core entity of the app.

All endpoints require authentication. Any member of the account can
read and write transactions (no role gating here, unlike categories
where only owner/admin can modify the catalog).

💡 CONCEPT: Why members can write transactions
   In a household account, the family member doing the groceries should
   be able to record their spending without admin approval. The audit
   trail (`created_by`) tells you who did what.
"""

import datetime as dt
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import CurrentUser, DbSession
from app.models.enums import BudgetBucket, TransactionType
from app.schemas.transaction import (
    TransactionCreate,
    TransactionListResponse,
    TransactionResponse,
    TransactionUpdate,
)
from app.services import transaction as transaction_service
from app.services.transaction import (
    CategoryInvalidError,
    TransactionNotFoundError,
)

router = APIRouter(
    prefix="/api/transactions",
    tags=["transactions"],
)


# ============================================================
# GET /api/transactions
# ============================================================

@router.get("", response_model=TransactionListResponse)
def list_transactions(
    user: CurrentUser,
    db: DbSession,
    # --- Filters ---
    date_from: Annotated[
        dt.date | None,
        Query(description="Inclusive lower bound on transaction date (YYYY-MM-DD)."),
    ] = None,
    date_to: Annotated[
        dt.date | None,
        Query(description="Inclusive upper bound on transaction date (YYYY-MM-DD)."),
    ] = None,
    type: Annotated[
        TransactionType | None,
        Query(description="Filter by transaction type."),
    ] = None,
    category_id: Annotated[
        int | None,
        Query(gt=0, description="Filter by category."),
    ] = None,
    budget_bucket: Annotated[
        BudgetBucket | None,
        Query(description="Filter by 50/30/20 bucket."),
    ] = None,
    search: Annotated[
        str | None,
        Query(min_length=1, max_length=100, description="Substring match on description."),
    ] = None,
    tags: Annotated[
        list[str] | None,
        Query(description="Match transactions tagged with ANY of these names."),
    ] = None,
    # --- Pagination ---
    page: Annotated[int, Query(ge=1, description="1-indexed page number.")] = 1,
    per_page: Annotated[int, Query(ge=1, le=200, description="Items per page (max 200).")] = 50,
) -> TransactionListResponse:
    """List transactions, with any combination of filters and pagination.

    Result is ordered by date DESC, id DESC (most recent first).
    """
    items, total = transaction_service.list_transactions(
        db,
        account_id=user.account_id,
        date_from=date_from,
        date_to=date_to,
        type=type,
        category_id=category_id,
        budget_bucket=budget_bucket,
        search=search,
        tags=tags,
        page=page,
        per_page=per_page,
    )

    return TransactionListResponse(
        items=[TransactionResponse.model_validate(t) for t in items],
        page=page,
        per_page=per_page,
        total=total,
        total_pages=transaction_service.total_pages(total, per_page),
    )


# ============================================================
# GET /api/transactions/{id}
# ============================================================

@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: int,
    user: CurrentUser,
    db: DbSession,
) -> TransactionResponse:
    """Get a single transaction by ID."""
    try:
        transaction = transaction_service.get_transaction(
            db,
            account_id=user.account_id,
            transaction_id=transaction_id,
        )
    except TransactionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return TransactionResponse.model_validate(transaction)


# ============================================================
# POST /api/transactions
# ============================================================

@router.post(
    "",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_transaction(
    payload: TransactionCreate,
    user: CurrentUser,
    db: DbSession,
) -> TransactionResponse:
    """Create a new transaction.

    The current user is automatically recorded as `created_by`. Tags are
    auto-created if they don't exist.

    Returns 409 Conflict if the referenced category is archived or
    doesn't exist in this account.
    """
    try:
        transaction = transaction_service.create_transaction(
            db,
            account_id=user.account_id,
            creator=user,
            payload=payload,
        )
    except CategoryInvalidError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return TransactionResponse.model_validate(transaction)


# ============================================================
# PUT /api/transactions/{id}
# ============================================================

@router.put("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    user: CurrentUser,
    db: DbSession,
) -> TransactionResponse:
    """Update a transaction (partial — send only fields to change).

    Tags semantics:
    - Omitting `tags` leaves them unchanged.
    - `"tags": []` clears all tags.
    - `"tags": ["a", "b"]` replaces the tag list with exactly those.
    """
    try:
        transaction = transaction_service.update_transaction(
            db,
            account_id=user.account_id,
            transaction_id=transaction_id,
            payload=payload,
        )
    except TransactionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except CategoryInvalidError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return TransactionResponse.model_validate(transaction)


# ============================================================
# DELETE /api/transactions/{id}
# ============================================================

@router.delete(
    "/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_transaction(
    transaction_id: int,
    user: CurrentUser,
    db: DbSession,
) -> None:
    """Permanently delete a transaction.

    Returns 204 No Content on success (no response body).
    """
    try:
        transaction_service.delete_transaction(
            db,
            account_id=user.account_id,
            transaction_id=transaction_id,
        )
    except TransactionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
