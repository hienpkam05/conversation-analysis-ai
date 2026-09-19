"""Bo sung updated_at cho embedding_refs.

Revision ID: 20260919_0002
Revises: 20260919_0001
Create Date: 2026-09-19
"""

from alembic import op
import sqlalchemy as sa


revision = "20260919_0002"
down_revision = "20260919_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "embedding_refs",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("embedding_refs", "updated_at")
