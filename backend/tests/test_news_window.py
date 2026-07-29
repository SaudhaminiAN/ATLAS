"""News window evaluation tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from atlas.domain.models.news import EconomicEvent, EventImpact
from atlas.domain.services.news_window import NewsFilterConfig, compute_news_status

CONFIG = NewsFilterConfig(
    hard_block_minutes_before=15,
    hard_block_minutes_after=15,
    soft_downgrade_minutes_before=30,
    soft_downgrade_minutes_after=30,
    soft_downgrade_penalty=Decimal("0.20"),
)


def _event(name: str, scheduled_at: datetime) -> EconomicEvent:
    return EconomicEvent(
        id=uuid4(),
        name=name,
        currency="USD",
        impact=EventImpact.HIGH,
        scheduled_at=scheduled_at,
        source="test",
    )


def test_hard_block_at_event_time() -> None:
    event_time = datetime(2026, 1, 15, 12, 30, tzinfo=UTC)
    status = compute_news_status([_event("US CPI", event_time)], event_time, CONFIG)
    assert status.is_blocked is True
    assert status.is_soft_downgrade is False
    assert status.confluence_penalty == Decimal("0")


def test_hard_block_boundary_before() -> None:
    event_time = datetime(2026, 1, 15, 12, 30, tzinfo=UTC)
    as_of = event_time - timedelta(minutes=15)
    status = compute_news_status([_event("US CPI", event_time)], as_of, CONFIG)
    assert status.is_blocked is True


def test_soft_downgrade_before_hard_window() -> None:
    event_time = datetime(2026, 1, 15, 12, 30, tzinfo=UTC)
    as_of = event_time - timedelta(minutes=20)
    status = compute_news_status([_event("US CPI", event_time)], as_of, CONFIG)
    assert status.is_blocked is False
    assert status.is_soft_downgrade is True
    assert status.confluence_penalty == Decimal("0.20")


def test_clear_outside_windows() -> None:
    event_time = datetime(2026, 1, 15, 12, 30, tzinfo=UTC)
    as_of = event_time - timedelta(minutes=31)
    status = compute_news_status([_event("US CPI", event_time)], as_of, CONFIG)
    assert status.is_blocked is False
    assert status.is_soft_downgrade is False
    assert status.confluence_penalty == Decimal("0")


def test_overlapping_events_block_wins() -> None:
    base = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
    events = [
        _event("US CPI", base),
        _event("FOMC", base + timedelta(minutes=20)),
    ]
    as_of = base - timedelta(minutes=10)
    status = compute_news_status(events, as_of, CONFIG)
    assert status.is_blocked is True


def test_ignores_medium_and_low_impact() -> None:
    event_time = datetime(2026, 1, 15, 12, 30, tzinfo=UTC)
    medium = EconomicEvent(
        id=uuid4(),
        name="Minor Data",
        currency="USD",
        impact=EventImpact.MEDIUM,
        scheduled_at=event_time,
        source="test",
    )
    status = compute_news_status([medium], event_time, CONFIG)
    assert status.is_blocked is False
    assert status.is_soft_downgrade is False


def test_utc_normalization_from_naive_datetime() -> None:
    event_time = datetime(2026, 1, 15, 12, 30, tzinfo=UTC)
    as_of_naive = datetime(2026, 1, 15, 12, 30)
    status = compute_news_status([_event("US CPI", event_time)], as_of_naive, CONFIG)
    assert status.is_blocked is True


def test_next_event_is_nearest_future() -> None:
    now = datetime(2026, 1, 15, 10, 0, tzinfo=UTC)
    events = [
        _event("Later", now + timedelta(hours=3)),
        _event("Sooner", now + timedelta(hours=1)),
    ]
    status = compute_news_status(events, now, CONFIG)
    assert status.next_event is not None
    assert status.next_event.name == "Sooner"
