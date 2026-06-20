"""deployment schema: deployment_reports + repository homepage

Revision ID: 0003_deployment_schema
Revises: 0002_repository_schema
Create Date: 2026-06-20 13:00:00
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_deployment_schema"
down_revision: Union[str, None] = "0002_repository_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add homepage column to repositories table
    op.add_column("repositories", sa.Column("homepage", sa.String(length=2048), nullable=True))

    # 2. Create deployment_reports table
    op.create_table(
        "deployment_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("deployment_url", sa.String(length=2048), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("reachable", sa.Boolean(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("response_time", sa.Float(), nullable=True),
        sa.Column("ssl_enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("ssl_expiry_days", sa.Integer(), nullable=True),
        sa.Column("security_headers_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("asset_health_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("internal_link_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deployment_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE", name=op.f("fk_deployment_reports_repository_id_repositories")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deployment_reports")),
    )
    op.create_index(op.f("ix_deployment_reports_repository_id"), "deployment_reports", ["repository_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_deployment_reports_repository_id"), table_name="deployment_reports")
    op.drop_table("deployment_reports")
    op.drop_column("repositories", "homepage")
