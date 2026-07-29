"""Alembic migration: pipeline_runs table."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create pipeline_runs table."""
    op.create_table(
        "pipeline_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trigger_timeframe", sa.String(8), nullable=False),
        sa.Column("trigger_bar_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("stage_results", postgresql.JSONB(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pipeline_runs_correlation_id",
        "pipeline_runs",
        ["correlation_id"],
    )
    op.create_index(
        "ix_pipeline_runs_instrument_trigger",
        "pipeline_runs",
        ["instrument_id", "trigger_bar_time"],
    )


def downgrade() -> None:
    """Drop pipeline_runs table."""
    op.drop_index("ix_pipeline_runs_instrument_trigger", table_name="pipeline_runs")
    op.drop_index("ix_pipeline_runs_correlation_id", table_name="pipeline_runs")
    op.drop_table("pipeline_runs")
