"""Base domain event type."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """Immutable domain event published on the internal event bus."""

    event_type: str
    correlation_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.event_type:
            raise ValueError("event_type is required")
        if not self.correlation_id:
            raise ValueError("correlation_id is required")
