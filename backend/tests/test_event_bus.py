"""Event bus unit tests."""

from atlas.domain.events.base import DomainEvent
from atlas.infrastructure.events.in_memory_bus import InMemoryEventBus


def test_publish_delivers_to_subscriber() -> None:
    """Subscribed handler receives published event."""
    bus = InMemoryEventBus()
    received: list[DomainEvent] = []

    def handler(event: DomainEvent) -> None:
        received.append(event)

    bus.subscribe("test.event", handler)
    event = DomainEvent(event_type="test.event", correlation_id="cid-1", payload={"k": "v"})
    bus.publish(event)

    assert len(received) == 1
    assert received[0].event_type == "test.event"
    assert received[0].correlation_id == "cid-1"
    assert received[0].payload == {"k": "v"}


def test_unsubscribe_removes_handler() -> None:
    """Unsubscribed handler does not receive events."""
    bus = InMemoryEventBus()
    received: list[DomainEvent] = []

    def handler(event: DomainEvent) -> None:
        received.append(event)

    bus.subscribe("test.event", handler)
    bus.unsubscribe("test.event", handler)
    bus.publish(DomainEvent(event_type="test.event", correlation_id="cid-2"))

    assert received == []


def test_handler_error_does_not_stop_other_handlers() -> None:
    """One failing handler does not prevent others from running."""
    bus = InMemoryEventBus()
    received: list[str] = []

    def bad_handler(_: DomainEvent) -> None:
        raise RuntimeError("handler failed")

    def good_handler(_: DomainEvent) -> None:
        received.append("ok")

    bus.subscribe("test.event", bad_handler)
    bus.subscribe("test.event", good_handler)
    bus.publish(DomainEvent(event_type="test.event", correlation_id="cid-3"))

    assert received == ["ok"]
