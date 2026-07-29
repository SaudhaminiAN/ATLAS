"""Alembic migration: ohlcv_bars table."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create ohlcv_bars table."""
    op.create_table(
        "ohlcv_bars",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timeframe", sa.String(8), nullable=False),
        sa.Column("open_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(18, 6), nullable=False),
        sa.Column("high", sa.Numeric(18, 6), nullable=False),
        sa.Column("low", sa.Numeric(18, 6), nullable=False),
        sa.Column("close", sa.Numeric(18, 6), nullable=False),
        sa.Column("volume", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("is_outlier", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("quality_flags", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("instrument_id", "timeframe", "open_time", name="uq_ohlcv_bar"),
    )
    op.create_index(
        "ix_ohlcv_bars_lookup",
        "ohlcv_bars",
        ["instrument_id", "timeframe", "open_time"],
        unique=False,
    )


def downgrade() -> None:
    """Drop ohlcv_bars table."""
    op.drop_index("ix_ohlcv_bars_lookup", table_name="ohlcv_bars")
    op.drop_table("ohlcv_bars")
