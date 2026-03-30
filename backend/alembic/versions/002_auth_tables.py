"""Add auth tables.

Revision ID: 002_auth_tables
Revises: 001_baseline
Create Date: 2026-03-30
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "002_auth_tables"
down_revision = "001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("avatar_url", sa.String(length=512), nullable=True),
        sa.Column("locale", sa.String(length=10), server_default="zh-CN", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("idx_sessions_token", "sessions", ["token"], unique=False)
    op.create_index("idx_sessions_user", "sessions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_sessions_user", table_name="sessions")
    op.drop_index("idx_sessions_token", table_name="sessions")
    op.drop_table("sessions")
    op.drop_table("users")
