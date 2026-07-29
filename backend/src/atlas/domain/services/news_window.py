"""News window evaluation logic."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from atlas.domain.models.news import (
    EconomicEvent,
    EventImpact,
    NewsFilterStatus,
    NextEventInfo,
)
from atlas.domain.services.bar_validation import to_utc


@dataclass(frozen=True, slots=True)
class NewsFilterConfig:
    """Configurable news filter windows."""

    hard_block_minutes_before: int = 15
    hard_block_minutes_after: int = 15
    soft_downgrade_minutes_before: int = 30
    soft_downgrade_minutes_after: int = 30
    soft_downgrade_penalty: Decimal = Decimal("0.20")


def _in_window(as_of: datetime, center: datetime, before: timedelta, after: timedelta) -> bool:
    start = center - before
    end = center + after
    return start <= as_of <= end


def compute_news_status(
    events: list[EconomicEvent],
    as_of: datetime,
    config: NewsFilterConfig,
) -> NewsFilterStatus:
    """Evaluate block/downgrade state; overlapping events use worst case."""
    as_of_utc = to_utc(as_of)
    high_impact = [e for e in events if e.impact == EventImpact.HIGH]

    hard_before = timedelta(minutes=config.hard_block_minutes_before)
    hard_after = timedelta(minutes=config.hard_block_minutes_after)
    soft_before = timedelta(minutes=config.soft_downgrade_minutes_before)
    soft_after = timedelta(minutes=config.soft_downgrade_minutes_after)

    is_blocked = False
    is_soft = False

    for event in high_impact:
        scheduled = to_utc(event.scheduled_at)
        if _in_window(as_of_utc, scheduled, hard_before, hard_after):
            is_blocked = True
        elif _in_window(as_of_utc, scheduled, soft_before, soft_after):
            is_soft = True

    next_event = _nearest_future_event(high_impact, as_of_utc)

    if is_blocked:
        return NewsFilterStatus(
            is_blocked=True,
            is_soft_downgrade=False,
            confluence_penalty=Decimal("0"),
            next_event=next_event,
            as_of=as_of_utc,
        )

    return NewsFilterStatus(
        is_blocked=False,
        is_soft_downgrade=is_soft,
        confluence_penalty=config.soft_downgrade_penalty if is_soft else Decimal("0"),
        next_event=next_event,
        as_of=as_of_utc,
    )


def _nearest_future_event(events: list[EconomicEvent], as_of: datetime) -> NextEventInfo | None:
    future = [e for e in events if to_utc(e.scheduled_at) > as_of]
    if not future:
        return None
    nearest = min(future, key=lambda e: to_utc(e.scheduled_at))
    return NextEventInfo(name=nearest.name, scheduled_at=to_utc(nearest.scheduled_at))
