"""skills and project insights schema

Revision ID: 0004_skills_insights_schema
Revises: 0003_deployment_schema
Create Date: 2026-06-20 17:45:00
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_skills_insights_schema"
down_revision: Union[str, None] = "0003_deployment_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create skills table
    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("skill_name", sa.String(length=255), nullable=False),
        sa.Column("confidence_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE", name=op.f("fk_skills_repository_id_repositories")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_skills")),
    )
    op.create_index(op.f("ix_skills_repository_id"), "skills", ["repository_id"], unique=False)

    # 2. Create project_insights table
    op.create_table(
        "project_insights",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("project_type", sa.String(length=255), nullable=False),
        sa.Column("project_category", sa.JSON(), nullable=False),
        sa.Column("project_summary", sa.String(length=4096), nullable=False),
        sa.Column("technical_summary", sa.String(length=4096), nullable=False),
        sa.Column("complexity_level", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE", name=op.f("fk_project_insights_repository_id_repositories")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_project_insights")),
    )
    op.create_index(op.f("ix_project_insights_repository_id"), "project_insights", ["repository_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_project_insights_repository_id"), table_name="project_insights")
    op.drop_table("project_insights")
    op.drop_index(op.f("ix_skills_repository_id"), table_name="skills")
    op.drop_table("skills")
