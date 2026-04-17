"""
Alembic migration environment.

💡 CONCEPT: What env.py does
   Alembic runs this file every time you run an `alembic` command.
   It's responsible for:
   1. Telling Alembic WHICH DATABASE to operate on
   2. Telling Alembic WHICH METADATA to compare against (for autogenerate)
   3. Running the actual migrations

   The generic template ships with placeholders for both; we fill them in
   using our app's existing config and models.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Import our app's settings and models.
# IMPORTANT: importing app.models ensures all model classes get registered
# on Base.metadata. Without this, Alembic would only see an empty schema.
from app.config import settings
from app.database import Base
from app import models  # noqa: F401 — needed for side effect (registers models)

# --- Alembic config ---
config = context.config

# Override the sqlalchemy.url from alembic.ini with our app's DATABASE_URL.
# This way we have ONE source of truth for the database URL (app/config.py).
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# --- Logging ---
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- Metadata ---
# This is what Alembic compares against the real DB to detect changes.
# Because we imported `app.models` above, Base.metadata now contains all
# tables (accounts, users, transactions, etc.).
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Generates SQL scripts without actually connecting to the DB.
    Useful for review or applying manually.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Render types with precision/length (e.g., VARCHAR(100) instead of VARCHAR)
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Connects to the database and applies migrations directly.
    This is what you'll use 99% of the time.

    💡 CONCEPT: render_as_batch for SQLite
       SQLite has limited ALTER TABLE support (no ALTER COLUMN, no DROP
       COLUMN in some versions, etc.). `render_as_batch=True` tells Alembic
       to use a workaround: create a new table, copy data, drop the old,
       rename. This makes SQLite migrations feel like regular ALTERs.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # Critical for SQLite compatibility
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
