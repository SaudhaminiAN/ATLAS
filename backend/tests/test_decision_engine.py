"""Decision engine tests."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from atlas.application.decision.service import DecisionEngineService
from atlas.domain.models.confluence import ConfluenceResult
from atlas.domain.models.enums import Direction, Timeframe
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.news import NewsFilterStatus
from atlas.domain.models.strategy import StrategyProfile
from atlas.domain.models.validation import ValidationResult
from atlas.infrastructure.events.in_memory_bus import InMemoryEventBus


def _instrument() -> Instrument:
    return Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )


def _strategy(**overrides) -> StrategyProfile:
    base = dict(
        id="test",
        name="Test",
        min_confluence_score=Decimal("0.70"),
        enabled_directions=(Direction.BUY, Direction.SELL),
        confluence_weights={},
        active_timeframes=(Timeframe.H4,),
        allowed_sessions=(),
        validation_rule_flags={},
        is_active=True,
        updated_at=datetime.now(UTC),
    )
    base.update(overrides)
    return StrategyProfile(**base)


def _confluence(
    direction: Direction = Direction.BUY,
    total_score: Decimal = Decimal("0.80"),
) -> ConfluenceResult:
    return ConfluenceResult(
        instrument=_instrument(),
        suggested_direction=direction,
        total_score=total_score,
        raw_score=total_score,
        bullish_raw=Decimal("0.80"),
        bearish_raw=Decimal("0.05"),
        news_penalty=Decimal("0"),
        module_scores=(),
        evidence=(),
        evidence_count=4,
        has_conflict=False,
        strategy_profile_id="test",
        computed_at=datetime.now(UTC),
    )


def _validation(is_valid: bool = True) -> ValidationResult:
    return ValidationResult(
        instrument=_instrument(),
        direction=Direction.BUY,
        is_valid=is_valid,
        rules=(),
        failed_rules=() if is_valid else ("confluence_score_minimum",),
        strategy_profile_id="test",
        validated_at=datetime.now(UTC),
    )


def _news(blocked: bool = False) -> NewsFilterStatus:
    return NewsFilterStatus(
        is_blocked=blocked,
        is_soft_downgrade=False,
        confluence_penalty=Decimal("0"),
        next_event=None,
        as_of=datetime.now(UTC),
    )


def _engine() -> DecisionEngineService:
    return DecisionEngineService(event_bus=InMemoryEventBus())


def test_actionable_buy_when_all_checks_pass() -> None:
    decision = _engine().resolve(
        _confluence(),
        _validation(),
        _news(),
        _strategy(),
        correlation_id="cid",
    )
    assert decision.direction == Direction.BUY
    assert decision.is_actionable is True
    assert decision.confluence_snapshot is not None


def test_actionable_sell() -> None:
    decision = _engine().resolve(
        _confluence(direction=Direction.SELL),
        _validation(),
        _news(),
        _strategy(),
        correlation_id="cid",
    )
    assert decision.direction == Direction.SELL
    assert decision.is_actionable is True


def test_wait_when_news_blocked() -> None:
    decision = _engine().resolve(
        _confluence(),
        _validation(),
        _news(blocked=True),
        _strategy(),
        correlation_id="cid",
    )
    assert decision.direction == Direction.WAIT
    assert decision.is_actionable is False


def test_wait_when_validation_fails() -> None:
    decision = _engine().resolve(
        _confluence(),
        _validation(is_valid=False),
        _news(),
        _strategy(),
        correlation_id="cid",
    )
    assert decision.direction == Direction.WAIT


def test_wait_when_confluence_below_threshold() -> None:
    decision = _engine().resolve(
        _confluence(total_score=Decimal("0.50")),
        _validation(),
        _news(),
        _strategy(),
        correlation_id="cid",
    )
    assert decision.direction == Direction.WAIT
    assert "threshold" in decision.reason


def test_wait_when_direction_disabled() -> None:
    decision = _engine().resolve(
        _confluence(direction=Direction.SELL),
        _validation(),
        _news(),
        _strategy(enabled_directions=(Direction.BUY,)),
        correlation_id="cid",
    )
    assert decision.direction == Direction.WAIT


def test_wait_when_risk_breached() -> None:
    decision = _engine().resolve(
        _confluence(),
        _validation(),
        _news(),
        _strategy(),
        correlation_id="cid",
        risk_within_limits=False,
    )
    assert decision.direction == Direction.WAIT
    assert "Risk" in decision.reason


def test_wait_when_suggested_direction_wait() -> None:
    decision = _engine().resolve(
        _confluence(direction=Direction.WAIT),
        _validation(),
        _news(),
        _strategy(),
        correlation_id="cid",
    )
    assert decision.direction == Direction.WAIT
    assert decision.reason == "Insufficient evidence"


@pytest.mark.asyncio
async def test_emit_publishes_event_and_persists() -> None:
    bus = InMemoryEventBus()
    events: list[str] = []
    bus.subscribe("decision.emitted", lambda e: events.append(e.event_type))

    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock(rowcount=1))
    session_factory = MagicMock()
    session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
    session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    cache = MagicMock()
    cache.set_latest = AsyncMock()

    engine = DecisionEngineService(
        event_bus=bus,
        session_factory=session_factory,
        decision_cache=cache,
    )
    decision = _engine().resolve(
        _confluence(),
        _validation(),
        _news(),
        _strategy(),
        correlation_id="cid",
    )
    await engine.emit(decision)

    assert events == ["decision.emitted"]
    cache.set_latest.assert_awaited_once()
