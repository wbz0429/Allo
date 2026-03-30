"""Add thread and user data tables.

Revision ID: 004_threads_and_user_data
Revises: 002_auth_tables
Create Date: 2026-03-30
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "004_threads_and_user_data"
down_revision = "002_auth_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "threads",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("agent_name", sa.String(length=100), nullable=True),
        sa.Column("default_model", sa.String(length=100), nullable=True),
        sa.Column("last_model_name", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_active_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_threads_user_id", "threads", ["user_id"], unique=False)
    op.create_index("ix_threads_org_id", "threads", ["org_id"], unique=False)
    op.create_index("ix_threads_last_active_at", "threads", ["last_active_at"], unique=False)

    op.create_table(
        "thread_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("thread_id", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("agent_name", sa.String(length=100), nullable=True),
        sa.Column("sandbox_id", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="running", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["thread_id"], ["threads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_thread_runs_thread_id", "thread_runs", ["thread_id"], unique=False)
    op.create_index("ix_thread_runs_user_id", "thread_runs", ["user_id"], unique=False)
    op.create_index("ix_thread_runs_org_id", "thread_runs", ["org_id"], unique=False)

    op.create_table(
        "user_memory",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("context_json", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_memory_user_id", "user_memory", ["user_id"], unique=False)
    op.create_index("ix_user_memory_org_id", "user_memory", ["org_id"], unique=False)

    op.create_table(
        "user_memory_facts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("memory_id", sa.String(length=36), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["memory_id"], ["user_memory.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_memory_facts_user_id", "user_memory_facts", ["user_id"], unique=False)
    op.create_index("ix_user_memory_facts_memory_id", "user_memory_facts", ["memory_id"], unique=False)

    op.create_table(
        "user_souls",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_souls_user_id", "user_souls", ["user_id"], unique=False)
    op.create_index("ix_user_souls_org_id", "user_souls", ["org_id"], unique=False)

    op.create_table(
        "user_mcp_configs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("config_json", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_mcp_configs_user_id", "user_mcp_configs", ["user_id"], unique=False)
    op.create_index("ix_user_mcp_configs_org_id", "user_mcp_configs", ["org_id"], unique=False)

    op.create_table(
        "user_agents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("tool_groups_json", sa.Text(), nullable=False),
        sa.Column("soul_content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_agents_user_id", "user_agents", ["user_id"], unique=False)
    op.create_index("ix_user_agents_org_id", "user_agents", ["org_id"], unique=False)

    op.create_table(
        "user_api_keys",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("api_key_enc", sa.Text(), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_api_keys_user_id", "user_api_keys", ["user_id"], unique=False)
    op.create_index("ix_user_api_keys_org_id", "user_api_keys", ["org_id"], unique=False)
    op.create_index("ix_user_api_keys_provider", "user_api_keys", ["provider"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_api_keys_provider", table_name="user_api_keys")
    op.drop_index("ix_user_api_keys_org_id", table_name="user_api_keys")
    op.drop_index("ix_user_api_keys_user_id", table_name="user_api_keys")
    op.drop_table("user_api_keys")

    op.drop_index("ix_user_agents_org_id", table_name="user_agents")
    op.drop_index("ix_user_agents_user_id", table_name="user_agents")
    op.drop_table("user_agents")

    op.drop_index("ix_user_mcp_configs_org_id", table_name="user_mcp_configs")
    op.drop_index("ix_user_mcp_configs_user_id", table_name="user_mcp_configs")
    op.drop_table("user_mcp_configs")

    op.drop_index("ix_user_souls_org_id", table_name="user_souls")
    op.drop_index("ix_user_souls_user_id", table_name="user_souls")
    op.drop_table("user_souls")

    op.drop_index("ix_user_memory_facts_memory_id", table_name="user_memory_facts")
    op.drop_index("ix_user_memory_facts_user_id", table_name="user_memory_facts")
    op.drop_table("user_memory_facts")

    op.drop_index("ix_user_memory_org_id", table_name="user_memory")
    op.drop_index("ix_user_memory_user_id", table_name="user_memory")
    op.drop_table("user_memory")

    op.drop_index("ix_thread_runs_org_id", table_name="thread_runs")
    op.drop_index("ix_thread_runs_user_id", table_name="thread_runs")
    op.drop_index("ix_thread_runs_thread_id", table_name="thread_runs")
    op.drop_table("thread_runs")

    op.drop_index("ix_threads_last_active_at", table_name="threads")
    op.drop_index("ix_threads_org_id", table_name="threads")
    op.drop_index("ix_threads_user_id", table_name="threads")
    op.drop_table("threads")
