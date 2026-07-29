"""Journal entries table (Spec 13 Phase 3)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "journal_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("trade_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entry_type", sa.String(32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tags", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["trade_id"], ["trades.id"]),
    )
    op.create_index("ix_journal_entries_trade_id", "journal_entries", ["trade_id"])
    op.create_index("ix_journal_entries_decision_id", "journal_entries", ["decision_id"])
    op.create_index("ix_journal_entries_created_at", "journal_entries", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_journal_entries_created_at", table_name="journal_entries")
    op.drop_index("ix_journal_entries_decision_id", table_name="journal_entries")
    op.drop_index("ix_journal_entries_trade_id", table_name="journal_entries")
    op.drop_table("journal_entries")
