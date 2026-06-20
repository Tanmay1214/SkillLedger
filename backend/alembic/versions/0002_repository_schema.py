"""repository schema: repositories, analyses, languages, frameworks, dependencies, contributors

Revision ID: 0002_repository_schema
Revises: 0001_initial_schema
Create Date: 2026-06-20 12:00:00
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_repository_schema"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. repositories table
    op.create_table(
        "repositories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("github_repo_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column("repo_url", sa.String(length=2048), nullable=False),
        sa.Column("description", sa.String(length=4096), nullable=True),
        sa.Column("stars", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("forks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("watchers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("default_branch", sa.String(length=255), nullable=False, server_default="main"),
        sa.Column("language", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name=op.f("fk_repositories_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_repositories")),
    )
    op.create_index(op.f("ix_repositories_github_repo_id"), "repositories", ["github_repo_id"], unique=True)
    op.create_index(op.f("ix_repositories_user_id"), "repositories", ["user_id"], unique=False)

    # 2. repository_analyses table
    op.create_table(
        "repository_analyses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("complexity_score", sa.Integer(), nullable=True),
        sa.Column("security_score", sa.Integer(), nullable=True),
        sa.Column("documentation_score", sa.Integer(), nullable=True),
        sa.Column("analysis_status", sa.String(length=50), nullable=False, server_default="queued"),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("findings", sa.JSON(), nullable=True),
        sa.Column("commits_info", sa.JSON(), nullable=True),
        sa.Column("doc_report", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE", name=op.f("fk_repository_analyses_repository_id_repositories")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_repository_analyses")),
    )
    op.create_index(op.f("ix_repository_analyses_repository_id"), "repository_analyses", ["repository_id"], unique=False)

    # 3. languages table
    op.create_table(
        "languages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("language_name", sa.String(length=255), nullable=False),
        sa.Column("percentage", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE", name=op.f("fk_languages_repository_id_repositories")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_languages")),
    )
    op.create_index(op.f("ix_languages_repository_id"), "languages", ["repository_id"], unique=False)

    # 4. frameworks table
    op.create_table(
        "frameworks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("framework_name", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE", name=op.f("fk_frameworks_repository_id_repositories")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_frameworks")),
    )
    op.create_index(op.f("ix_frameworks_repository_id"), "frameworks", ["repository_id"], unique=False)

    # 5. dependencies table
    op.create_table(
        "dependencies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("dependency_name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE", name=op.f("fk_dependencies_repository_id_repositories")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dependencies")),
    )
    op.create_index(op.f("ix_dependencies_repository_id"), "dependencies", ["repository_id"], unique=False)

    # 6. contributors table
    op.create_table(
        "contributors",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("github_user_id", sa.BigInteger(), nullable=True),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("commits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("additions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deletions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ownership_percentage", sa.Float(), nullable=False, server_default="0.0"),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE", name=op.f("fk_contributors_repository_id_repositories")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contributors")),
    )
    op.create_index(op.f("ix_contributors_repository_id"), "contributors", ["repository_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_contributors_repository_id"), table_name="contributors")
    op.drop_table("contributors")
    op.drop_index(op.f("ix_dependencies_repository_id"), table_name="dependencies")
    op.drop_table("dependencies")
    op.drop_index(op.f("ix_frameworks_repository_id"), table_name="frameworks")
    op.drop_table("frameworks")
    op.drop_index(op.f("ix_languages_repository_id"), table_name="languages")
    op.drop_table("languages")
    op.drop_index(op.f("ix_repository_analyses_repository_id"), table_name="repository_analyses")
    op.drop_table("repository_analyses")
    op.drop_index(op.f("ix_repositories_user_id"), table_name="repositories")
    op.drop_index(op.f("ix_repositories_github_repo_id"), table_name="repositories")
    op.drop_table("repositories")
