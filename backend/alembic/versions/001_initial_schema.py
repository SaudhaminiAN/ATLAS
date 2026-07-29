"""Initial schema: instruments, strategy_profiles, schema_metadata."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_STRATEGY = {
    "id": "xauusd_conservative",
    "name": "XAUUSD Conservative",
    "min_confluence_score": 0.70,
    "enabled_directions": ["BUY", "SELL"],
    "confluence_weights": {
        "mtf_alignment": 0.25,
        "smc_structure": 0.25,
        "price_action": 0.20,
        "technical_levels": 0.15,
        "market_context": 0.15,
    },
    "active_timeframes": ["D1", "H4", "H1", "M15"],
    "allowed_sessions": ["london", "new_york", "overlap"],
    "validation_rules": {
        "mtf_alignment_minimum": True,
        "confluence_score_minimum": True,
        "no_counter_trend": True,
        "minimum_rr_potential": True,
        "news_block": True,
        "session_check": True,
        "spread_check": True,
        "volatility_check": True,
    },
}


def upgrade() -> None:
    """Create initial tables and seed XAUUSD data."""
    op.create_table(
        "instruments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("symbol", sa.String(32), nullable=False, unique=True),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("pip_size", sa.Numeric(12, 6), nullable=False),
        sa.Column("lot_size", sa.Numeric(12, 4), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "strategy_profiles",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "schema_metadata",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
    )

    op.execute(
        sa.text(
            """
            INSERT INTO instruments (id, symbol, display_name, pip_size, lot_size, is_active)
            VALUES (
                gen_random_uuid(),
                'XAUUSD',
                'Gold / US Dollar',
                0.01,
                100.0,
                true
            )
            """
        )
    )

    import json

    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            INSERT INTO strategy_profiles (id, name, config, is_active)
            VALUES (:id, :name, CAST(:config AS jsonb), true)
            """
        ),
        {
            "id": DEFAULT_STRATEGY["id"],
            "name": DEFAULT_STRATEGY["name"],
            "config": json.dumps(DEFAULT_STRATEGY),
        },
    )

    op.execute(
        sa.text(
            """
            INSERT INTO schema_metadata (key, value)
            VALUES ('version', '001')
            """
        )
    )


def downgrade() -> None:
    """Drop initial tables."""
    op.drop_table("schema_metadata")
    op.drop_table("strategy_profiles")
    op.drop_table("instruments")
