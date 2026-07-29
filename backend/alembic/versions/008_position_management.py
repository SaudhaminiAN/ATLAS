"""Position management columns on trades (Spec 12)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "trades",
        sa.Column("initial_stop_loss", sa.Numeric(18, 6), nullable=True),
    )
    op.add_column(
        "trades",
        sa.Column("remaining_size", sa.Numeric(18, 4), nullable=True),
    )
    op.add_column(
        "trades",
        sa.Column(
            "partial_realized_pnl",
            sa.Numeric(18, 6),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "trades",
        sa.Column(
            "breakeven_applied",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "trades",
        sa.Column(
            "partial_exit_applied",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.execute(
        """
        UPDATE trades
        SET initial_stop_loss = stop_loss,
            remaining_size = position_size
        WHERE status IN ('open', 'partial')
        """
    )
    op.execute(
        """
        UPDATE trades
        SET initial_stop_loss = stop_loss,
            remaining_size = position_size
        WHERE initial_stop_loss IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("trades", "partial_exit_applied")
    op.drop_column("trades", "breakeven_applied")
    op.drop_column("trades", "partial_realized_pnl")
    op.drop_column("trades", "remaining_size")
    op.drop_column("trades", "initial_stop_loss")
