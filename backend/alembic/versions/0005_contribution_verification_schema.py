"""contribution verification schema

Revision ID: 0005_contribution_verification_schema
Revises: 0004_skills_insights_schema
Create Date: 2026-06-20 18:00:00
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_contribution_verification_schema"
down_revision: Union[str, None] = "0004_skills_insights_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update contributors table
    op.add_column("contributors", sa.Column("avatar_url", sa.String(length=2048), nullable=True))
    op.add_column("contributors", sa.Column("activity_score", sa.Integer(), nullable=True))
    op.add_column("contributors", sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))

    # 2. Create contribution_reports table
    op.create_table(
        "contribution_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("primary_contributor", sa.String(length=255), nullable=False),
        sa.Column("ownership_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("activity_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("contribution_summary", sa.String(length=4096), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE", name=op.f("fk_contribution_reports_repository_id_repositories")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contribution_reports")),
    )
    op.create_index(op.f("ix_contribution_reports_repository_id"), "contribution_reports", ["repository_id"], unique=False)

    # 3. Create module_ownerships table
    op.create_table(
        "module_ownerships",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("module_name", sa.String(length=255), nullable=False),
        sa.Column("ownership_percentage", sa.Float(), nullable=False, server_default="0.0"),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE", name=op.f("fk_module_ownerships_repository_id_repositories")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_module_ownerships")),
    )
    op.create_index(op.f("ix_module_ownerships_repository_id"), "module_ownerships", ["repository_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_module_ownerships_repository_id"), table_name="module_ownerships")
    op.drop_table("module_ownerships")
    op.drop_index(op.f("ix_contribution_reports_repository_id"), table_name="contribution_reports")
    op.drop_table("contribution_reports")
    op.drop_column("contributors", "created_at")
    op.drop_column("contributors", "activity_score")
    op.drop_column("contributors", "avatar_url")
