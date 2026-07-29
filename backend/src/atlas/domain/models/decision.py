"""Trading decision domain model."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from atlas.domain.models.confluence import ConfluenceResult
from atlas.domain.models.enums import Direction
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.news import NewsFilterStatus
from atlas.domain.models.validation import ValidationResult


@dataclass(frozen=True, slots=True)
class TradingDecision:
    """Final BUY / SELL / WAIT decision."""

    id: UUID
    instrument: Instrument
    direction: Direction
    is_actionable: bool
    confluence_score: Decimal
    strategy_id: str
    reason: str
    correlation_id: str
    decided_at: datetime
    confluence_snapshot: ConfluenceResult | None = None
    validation_snapshot: ValidationResult | None = None
    risk_snapshot: dict | None = None
    news_status: NewsFilterStatus | None = None


def wait_decision(
    instrument: Instrument,
    reason: str,
    *,
    correlation_id: str,
    strategy_id: str,
    confluence_score: Decimal = Decimal("0"),
    confluence: ConfluenceResult | None = None,
    validation: ValidationResult | None = None,
    news_status: NewsFilterStatus | None = None,
    decided_at: datetime | None = None,
) -> TradingDecision:
    """Build a non-actionable WAIT decision."""
    from datetime import UTC

    return TradingDecision(
        id=uuid4(),
        instrument=instrument,
        direction=Direction.WAIT,
        is_actionable=False,
        confluence_score=confluence_score,
        strategy_id=strategy_id,
        reason=reason,
        correlation_id=correlation_id,
        decided_at=decided_at or datetime.now(UTC),
        confluence_snapshot=confluence,
        validation_snapshot=validation,
        news_status=news_status,
    )
