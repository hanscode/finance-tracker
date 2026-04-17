"""
Setup router — first-time installation wizard.

Exposes two endpoints:
- GET  /api/setup/status  → is this install configured yet?
- POST /api/setup         → perform the one-time setup

💡 CONCEPT: APIRouter
   An APIRouter is like a mini FastAPI app. We group related endpoints
   into a router, then attach it to the main app:

       app.include_router(setup_router)

   Benefits: tag-based grouping in Swagger, prefix sharing, independent
   testability.
"""

from fastapi import APIRouter, HTTPException, status

from app.dependencies import DbSession
from app.schemas.setup import SetupRequest, SetupResponse, SetupStatusResponse
from app.services import setup as setup_service

router = APIRouter(
    prefix="/api/setup",
    tags=["setup"],
)


@router.get("/status", response_model=SetupStatusResponse)
def setup_status(db: DbSession) -> SetupStatusResponse:
    """Check if the initial setup has been completed.

    The frontend uses this on load to decide whether to show the setup
    wizard or the login screen.
    """
    account = setup_service.get_account(db)

    if account is None:
        return SetupStatusResponse(setup_completed=False, auth_method=None)

    return SetupStatusResponse(
        setup_completed=account.setup_completed,
        auth_method=account.auth_method,
    )


@router.post(
    "",
    response_model=SetupResponse,
    status_code=status.HTTP_201_CREATED,
)
def complete_setup(payload: SetupRequest, db: DbSession) -> SetupResponse:
    """Perform the first-time setup.

    Creates:
    - The singleton Account
    - AccountSettings with the chosen currency
    - The Owner user (with bcrypt-hashed password)
    - Default categories (income, needs, wants, savings)

    Returns 409 Conflict if setup has already been completed.
    """
    try:
        setup_service.create_initial_account(
            db,
            account_name=payload.account_name,
            owner_email=payload.owner_email,
            owner_name=payload.owner_name,
            owner_password=payload.owner_password,
            currency=payload.currency,
        )
    except ValueError as exc:
        # The service raises ValueError when setup is already done
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return SetupResponse()
