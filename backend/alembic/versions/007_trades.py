"""Trades and trade_events tables (Spec 11)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trades",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("direction", sa.String(8), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("entry_price", sa.Numeric(18, 6), nullable=False),
        sa.Column("fill_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("stop_loss", sa.Numeric(18, 6), nullable=False),
        sa.Column("take_profit", sa.Numeric(18, 6), nullable=False),
        sa.Column("position_size", sa.Numeric(18, 4), nullable=False),
        sa.Column("execution_mode", sa.String(16), nullable=False),
        sa.Column("rejection_reason", sa.String(512), nullable=True),
        sa.Column("realized_pnl", sa.Numeric(18, 6), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"]),
    )
    op.create_index("ix_trades_instrument_status", "trades", ["instrument_id", "status"])
    op.create_index("ix_trades_opened_at", "trades", ["opened_at"])

    op.create_table(
        "trade_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trade_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["trade_id"], ["trades.id"]),
    )
    op.create_index("ix_trade_events_trade_id", "trade_events", ["trade_id"])


def downgrade() -> None:
    op.drop_index("ix_trade_events_trade_id", table_name="trade_events")
    op.drop_table("trade_events")
    op.drop_index("ix_trades_opened_at", table_name="trades")
    op.drop_index("ix_trades_instrument_status", table_name="trades")
    op.drop_table("trades")
