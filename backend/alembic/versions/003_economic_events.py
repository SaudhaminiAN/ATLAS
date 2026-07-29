"""Alembic migration: economic_events table."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create economic_events table."""
    op.create_table(
        "economic_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("impact", sa.String(16), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actual", sa.Numeric(18, 6), nullable=True),
        sa.Column("forecast", sa.Numeric(18, 6), nullable=True),
        sa.Column("previous", sa.Numeric(18, 6), nullable=True),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_economic_events_scheduled_impact",
        "economic_events",
        ["scheduled_at", "impact"],
    )


def downgrade() -> None:
    """Drop economic_events table."""
    op.drop_index("ix_economic_events_scheduled_impact", table_name="economic_events")
    op.drop_table("economic_events")
