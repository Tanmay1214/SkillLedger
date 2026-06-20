"""Declarative base for all ORM models."""
from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Shared metadata with an explicit naming convention so that Alembic
# autogenerate produces deterministic, reviewable constraint names.
metadata = MetaData(naming_convention={
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
})


class Base(DeclarativeBase):
    """Project-wide declarative base.

    All models inherit from this so Alembic autogenerate and SQLAlchemy share
    one metadata registry.
    """

    metadata = metadata


__all__ = ["Base", "metadata"]
