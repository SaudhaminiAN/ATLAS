"""In-process event bus implementation."""

import structlog

from atlas.domain.events.base import DomainEvent
from atlas.domain.ports.event_bus import EventHandler

logger = structlog.get_logger(__name__)


class InMemoryEventBus:
    """Thread-safe enough for async single-process v1; synchronous dispatch."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}

    def publish(self, event: DomainEvent) -> None:
        """Publish event to subscribers; log and swallow handler errors."""
        handlers = list(self._handlers.get(event.event_type, []))
        handlers.extend(self._handlers.get("*", []))
        logger.debug(
            "event_published",
            event_type=event.event_type,
            correlation_id=event.correlation_id,
            handler_count=len(handlers),
        )
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                logger.exception(
                    "event_handler_failed",
                    event_type=event.event_type,
                    correlation_id=event.correlation_id,
                )

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Register handler."""
        self._handlers.setdefault(event_type, []).append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Remove handler if present."""
        if event_type not in self._handlers:
            return
        self._handlers[event_type] = [h for h in self._handlers[event_type] if h is not handler]
