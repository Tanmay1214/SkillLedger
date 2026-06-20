"""Alembic environment.

Uses the *sync* psycopg2 driver derived from DATABASE_URL so Alembic's
standard sync migration runner works. Targets our declarative metadata.
"""
from __future__ import annotations

import os
from logging.config import fileConfig
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from sqlalchemy import engine_from_config, pool

from alembic import context

# Make `app` importable.
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database.base import Base, metadata  # noqa: E402
import app.models  # noqa: F401, E402  # ensure models are registered on metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = metadata


def _resolve_sync_url() -> str:
    """Convert the async DSN in DATABASE_URL to a sync one for Alembic."""
    url = os.environ.get("DATABASE_URL", "")
    # asyncpg -> psycopg2
    url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    url = url.replace("postgresql://", "postgresql+psycopg2://")
    # aiosqlite -> sqlite (for sync Alembic runner)
    url = url.replace("sqlite+aiosqlite://", "sqlite://")
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_resolve_sync_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    config.set_main_option("sqlalchemy.url", _resolve_sync_url())
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
