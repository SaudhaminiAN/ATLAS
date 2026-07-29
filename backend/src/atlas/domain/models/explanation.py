"""AI explanation domain models (Spec 15)."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DecisionExplanation:
    """Natural-language explanation of a trading decision."""

    id: UUID
    decision_id: UUID
    content: str
    provider: str
    created_at: datetime
