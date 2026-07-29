"""Domain port interfaces (protocols)."""

from atlas.domain.ports.event_bus import EventBusProtocol, EventHandler

__all__ = ["EventBusProtocol", "EventHandler"]
