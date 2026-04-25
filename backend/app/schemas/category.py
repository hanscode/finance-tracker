"""
Pydantic schemas for the Category resource.

Three schemas, each for a different purpose:
- CategoryCreate   → what the client sends to POST /api/categories
- CategoryUpdate   → what the client sends to PUT /api/categories/{id}
- CategoryResponse → what the API returns

💡 CONCEPT: Why a separate schema for Update?
   On creation, fields like `name` are REQUIRED.
   On update, the client may send only the fields it wants to change
   ("PATCH semantics"). So `CategoryUpdate` makes everything optional.

   This is sometimes called the Create/Read/Update pattern, and most
   real-world APIs follow it.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import BudgetBucket, TransactionType

# ============================================================
# Shared field validation rules
# ============================================================
#
# 💡 CONCEPT: Hex color regex
#    `#RRGGBB` — 7 chars, starts with `#`, then 6 hex digits.
#    Lowercase or uppercase both fine. We don't accept the 3-char
#    form (#fff) for consistency.
HEX_COLOR_PATTERN = r"^#[0-9a-fA-F]{6}$"


# ============================================================
# POST /api/categories
# ============================================================

class CategoryCreate(BaseModel):
    """Payload to create a new category."""

    name: str = Field(
        min_length=1,
        max_length=100,
        description="Display name (e.g., 'Pet Care', 'Side Hustle').",
    )

    type: TransactionType = Field(
        description="What kind of transactions this category is for.",
    )

    budget_bucket: BudgetBucket | None = Field(
        default=None,
        description=(
            "50/30/20 classification. Required for expense categories so "
            "the budget engine can track them. Leave null for income."
        ),
    )

    icon: str | None = Field(
        default=None,
        max_length=50,
        description="Lucide icon name (e.g., 'shopping-cart', 'home').",
    )

    color: str | None = Field(
        default=None,
        pattern=HEX_COLOR_PATTERN,
        description="Hex color for the UI (e.g., '#ef4444').",
    )


# ============================================================
# PUT /api/categories/{id}
# ============================================================

class CategoryUpdate(BaseModel):
    """Payload to update a category. All fields optional (PATCH semantics).

    💡 CONCEPT: ConfigDict(extra='forbid')
       By default, Pydantic ignores unknown fields silently. We turn that
       off here so a typo like `{"naem": "Foo"}` (instead of "name") gets
       rejected with a 422 — saves frustrating "why isn't my change
       saving?" debugging.
    """
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    type: TransactionType | None = None
    budget_bucket: BudgetBucket | None = None
    icon: str | None = Field(default=None, max_length=50)
    color: str | None = Field(default=None, pattern=HEX_COLOR_PATTERN)


# ============================================================
# Response schema (used by all GET endpoints + as POST/PUT response)
# ============================================================

class CategoryResponse(BaseModel):
    """Public shape of a Category in API responses.

    💡 CONCEPT: from_attributes=True
       Lets Pydantic read fields from a SQLAlchemy model directly:
           CategoryResponse.model_validate(category_row)
       Without it we'd have to manually convert the row to a dict first.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: TransactionType
    budget_bucket: BudgetBucket | None
    icon: str | None
    color: str | None
    is_default: bool
    is_archived: bool
