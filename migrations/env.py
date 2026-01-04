"""
Alembic Environment Configuration

This file configures Alembic to work with the GlassTrax Bridge database.
It imports all models so that autogenerate can detect schema changes.
"""

from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context

# Import the SQLAlchemy Base and all models for autogenerate detection
from api.database import Base, DATABASE_URL
from api.models import Tenant, APIKey, AccessLog  # noqa: F401 - needed for autogenerate

# This is the Alembic Config object
config = context.config

# Override sqlalchemy.url with the app's database URL
# This ensures migrations use the same database as the app
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine.
    Calls to context.execute() emit SQL to the script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # SQLite-specific: enable batch mode for ALTER TABLE operations
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    Creates an Engine and associates a connection with the context.
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
            # SQLite-specific: enable batch mode for ALTER TABLE operations
            # This is required because SQLite doesn't support ALTER TABLE ADD COLUMN
            # with constraints, foreign keys, etc.
            render_as_batch=True,
            # Compare types to detect column type changes
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
