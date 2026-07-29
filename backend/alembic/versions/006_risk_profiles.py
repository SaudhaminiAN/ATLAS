"""Risk profiles table (Spec 10)."""

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_PROFILE = {
    "id": "default",
    "account_balance": 10000.0,
    "max_risk_percent": 1.0,
    "max_daily_loss_percent": 3.0,
    "max_open_positions": 2,
    "min_rr": 2.0,
    "buffer_atr_multiplier": 0.2,
    "max_sl_distance_atr": 3.0,
    "min_sl_pips": 5,
    "min_lot": 0.01,
    "lot_step": 0.01,
}


def upgrade() -> None:
    op.create_table(
        "risk_profiles",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("config", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            INSERT INTO risk_profiles (id, config)
            VALUES (:id, CAST(:config AS jsonb))
            """
        ),
        {"id": DEFAULT_PROFILE["id"], "config": json.dumps(DEFAULT_PROFILE)},
    )


def downgrade() -> None:
    op.drop_table("risk_profiles")
