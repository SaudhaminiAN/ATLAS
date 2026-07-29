"""AI explanation API DTOs."""

from datetime import datetime

from pydantic import BaseModel


class DecisionExplanationDTO(BaseModel):
    id: str
    decision_id: str
    content: str
    provider: str
    created_at: datetime
