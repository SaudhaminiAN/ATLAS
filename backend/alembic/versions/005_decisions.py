"""Alembic migration: decisions table."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create decisions table."""
    op.create_table(
        "decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column("direction", sa.String(8), nullable=False),
        sa.Column("is_actionable", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.String(512), nullable=False),
        sa.Column("confidence", sa.Numeric(6, 4), nullable=False),
        sa.Column("strategy_profile_id", sa.String(64), nullable=False),
        sa.Column("confluence_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("validation_result", postgresql.JSONB(), nullable=True),
        sa.Column("risk_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("news_status", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"]),
        sa.ForeignKeyConstraint(["strategy_profile_id"], ["strategy_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decisions_correlation_id", "decisions", ["correlation_id"])
    op.create_index(
        "ix_decisions_instrument_created",
        "decisions",
        ["instrument_id", "created_at"],
    )


def downgrade() -> None:
    """Drop decisions table."""
    op.drop_index("ix_decisions_instrument_created", table_name="decisions")
    op.drop_index("ix_decisions_correlation_id", table_name="decisions")
    op.drop_table("decisions")
