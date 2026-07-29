"""Decision explanations table (Spec 15)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "decision_explanations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["decision_id"], ["decisions.id"]),
    )
    op.create_index(
        "ix_decision_explanations_decision_id",
        "decision_explanations",
        ["decision_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_decision_explanations_decision_id", table_name="decision_explanations")
    op.drop_table("decision_explanations")
