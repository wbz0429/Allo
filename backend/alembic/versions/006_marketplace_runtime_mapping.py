"""add runtime mapping fields to marketplace items

Revision ID: 006_marketplace_runtime_mapping
Revises: 005_user_skill_configs
Create Date: 2026-04-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "006_marketplace_runtime_mapping"
down_revision: str | None = "005_user_skill_configs"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("marketplace_skills", sa.Column("runtime_skill_name", sa.String(length=255), nullable=True))
    op.add_column("marketplace_tools", sa.Column("runtime_tool_name", sa.String(length=255), nullable=True))

    op.execute("UPDATE marketplace_skills SET runtime_skill_name='deep-research' WHERE id='skill-deep-research'")
    op.execute("UPDATE marketplace_skills SET runtime_skill_name='data-analysis' WHERE id='skill-data-analysis'")
    op.execute("UPDATE marketplace_tools SET runtime_tool_name='web_search' WHERE id='tool-tavily-search'")
    op.execute("UPDATE marketplace_tools SET runtime_tool_name='bash' WHERE id='tool-code-sandbox'")


def downgrade() -> None:
    op.drop_column("marketplace_tools", "runtime_tool_name")
    op.drop_column("marketplace_skills", "runtime_skill_name")
