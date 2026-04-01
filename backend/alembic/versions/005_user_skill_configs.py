"""add user skill configs

Revision ID: 005_user_skill_configs
Revises: 004_threads_and_user_data
Create Date: 2026-04-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005_user_skill_configs"
down_revision: str | None = "004_threads_and_user_data"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_skill_configs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("config_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_skill_configs_user_id", "user_skill_configs", ["user_id"], unique=False)
    op.create_index("ix_user_skill_configs_org_id", "user_skill_configs", ["org_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_skill_configs_org_id", table_name="user_skill_configs")
    op.drop_index("ix_user_skill_configs_user_id", table_name="user_skill_configs")
    op.drop_table("user_skill_configs")
