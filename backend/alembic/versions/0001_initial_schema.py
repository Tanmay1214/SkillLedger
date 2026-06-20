"""initial schema: users + refresh_sessions

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-20 00:00:00
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("github_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("avatar_url", sa.String(length=2048), nullable=True),
        sa.Column("profile_url", sa.String(length=2048), nullable=True),
        sa.Column("access_token", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_github_id"), "users", ["github_id"], unique=True)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)

    op.create_table(
        "refresh_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name=op.f("fk_refresh_sessions_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_sessions")),
    )
    op.create_index(op.f("ix_refresh_sessions_jti"), "refresh_sessions", ["jti"], unique=True)
    op.create_index(op.f("ix_refresh_sessions_user_id"), "refresh_sessions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_refresh_sessions_user_id"), table_name="refresh_sessions")
    op.drop_index(op.f("ix_refresh_sessions_jti"), table_name="refresh_sessions")
    op.drop_table("refresh_sessions")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_github_id"), table_name="users")
    op.drop_table("users")
