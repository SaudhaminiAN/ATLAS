"""Internal event bus port."""

from collections.abc import Callable
from typing import Protocol

from atlas.domain.events.base import DomainEvent

EventHandler = Callable[[DomainEvent], None]


class EventBusProtocol(Protocol):
    """Publish/subscribe contract for in-process domain events."""

    def publish(self, event: DomainEvent) -> None:
        """Publish an event to all subscribers."""
        ...

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Register a handler for an event type."""
        ...

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Remove a handler for an event type."""
        ...
