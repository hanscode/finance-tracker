"""
Shared base classes and mixins for SQLAlchemy models.

💡 CONCEPT: Mixins
   A mixin is a class designed to add functionality to OTHER classes via
   multiple inheritance. It's NOT meant to be instantiated on its own.

   Example without mixins (repetitive):
       class Account(Base):
           id: Mapped[int] = mapped_column(primary_key=True)
           created_at: Mapped[datetime] = ...
           updated_at: Mapped[datetime] = ...

       class User(Base):
           id: Mapped[int] = mapped_column(primary_key=True)
           created_at: Mapped[datetime] = ...   # ← duplicated
           updated_at: Mapped[datetime] = ...   # ← duplicated

   Example with mixin (DRY):
       class Account(Base, TimestampMixin):
           id: Mapped[int] = mapped_column(primary_key=True)
           # created_at and updated_at come from the mixin

       class User(Base, TimestampMixin):
           id: Mapped[int] = mapped_column(primary_key=True)
           # same here, no duplication

💡 CONCEPT: Python multiple inheritance
   Python lets a class inherit from multiple parents:
       class MyModel(Base, TimestampMixin, SoftDeleteMixin):
           ...
   The class ends up with attributes from all three.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime.

    💡 CONCEPT: Why UTC everywhere?
       Timezones in software are a nightmare. The universally-accepted best
       practice is:
       1. Store all timestamps in UTC in the database
       2. Convert to the user's local timezone only at display time

       `datetime.now(timezone.utc)` gives us a timezone-aware UTC datetime.
       (Plain `datetime.now()` returns "naive" datetimes without tz info,
       which silently causes bugs.)
    """
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Adds `created_at` and `updated_at` columns to any model.

    - `created_at`: set once when the row is inserted, never changes.
    - `updated_at`: set on insert AND refreshed on every update.

    Usage:
        class User(Base, TimestampMixin):
            id: Mapped[int] = mapped_column(primary_key=True)
            # created_at and updated_at automatically included
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,          # Python-side default on INSERT
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,          # Set on INSERT
        onupdate=utcnow,         # Refreshed on every UPDATE
        nullable=False,
    )
