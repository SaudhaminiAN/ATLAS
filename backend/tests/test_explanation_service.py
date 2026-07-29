"""AI explanation service tests."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from atlas.application.ai.service import (
    AIExplanationService,
    DecisionNotFoundError,
    ExplanationRateLimitError,
)
from atlas.domain.models.decision import TradingDecision
from atlas.domain.models.enums import Direction
from atlas.domain.models.explanation import DecisionExplanation
from atlas.domain.models.instrument import Instrument
from atlas.infrastructure.ai.mock_provider import MockExplanationProvider


def _decision() -> TradingDecision:
    return TradingDecision(
        id=uuid4(),
        instrument=Instrument(
            id=uuid4(),
            symbol="XAUUSD",
            display_name="Gold",
            pip_size=Decimal("0.01"),
            lot_size=Decimal("100"),
        ),
        direction=Direction.WAIT,
        is_actionable=False,
        confluence_score=Decimal("0.55"),
        strategy_id="default",
        reason="Confluence below threshold",
        correlation_id="c1",
        decided_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_explain_returns_cached(monkeypatch) -> None:
    session = MagicMock()
    session_factory = MagicMock()
    session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
    session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    cached = DecisionExplanation(
        id=uuid4(),
        decision_id=uuid4(),
        content="Cached text",
        provider="mock",
        created_at=datetime.now(UTC),
    )
    repo = MagicMock()
    repo.get_by_decision_id = AsyncMock(return_value=cached)
    monkeypatch.setattr(
        "atlas.application.ai.service.ExplanationRepository",
        lambda _session: repo,
    )

    service = AIExplanationService(
        session_factory=session_factory,
        provider=MockExplanationProvider(),
        rate_limiter=MagicMock(allow=AsyncMock(return_value=True)),
    )
    result = await service.explain(cached.decision_id)
    assert result == cached


@pytest.mark.asyncio
async def test_explain_raises_when_decision_missing(monkeypatch) -> None:
    session = MagicMock()
    session_factory = MagicMock()
    session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
    session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    explain_repo = MagicMock()
    explain_repo.get_by_decision_id = AsyncMock(return_value=None)
    decision_repo = MagicMock()
    decision_repo.get_by_id = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "atlas.application.ai.service.ExplanationRepository",
        lambda _session: explain_repo,
    )
    monkeypatch.setattr(
        "atlas.application.ai.service.DecisionRepository",
        lambda _session: decision_repo,
    )

    service = AIExplanationService(
        session_factory=session_factory,
        provider=MockExplanationProvider(),
        rate_limiter=MagicMock(allow=AsyncMock(return_value=True)),
    )
    with pytest.raises(DecisionNotFoundError):
        await service.explain(uuid4())


@pytest.mark.asyncio
async def test_explain_rate_limited(monkeypatch) -> None:
    session = MagicMock()
    session_factory = MagicMock()
    session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
    session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    decision = _decision()
    explain_repo = MagicMock()
    explain_repo.get_by_decision_id = AsyncMock(return_value=None)
    decision_repo = MagicMock()
    decision_repo.get_by_id = AsyncMock(return_value=decision)
    monkeypatch.setattr(
        "atlas.application.ai.service.ExplanationRepository",
        lambda _session: explain_repo,
    )
    monkeypatch.setattr(
        "atlas.application.ai.service.DecisionRepository",
        lambda _session: decision_repo,
    )

    service = AIExplanationService(
        session_factory=session_factory,
        provider=MockExplanationProvider(),
        rate_limiter=MagicMock(allow=AsyncMock(return_value=False)),
    )
    with pytest.raises(ExplanationRateLimitError):
        await service.explain(decision.id)


@pytest.mark.asyncio
async def test_mock_provider_generates_text() -> None:
    decision = _decision()
    service = AIExplanationService(
        session_factory=MagicMock(),
        provider=MockExplanationProvider(),
        rate_limiter=MagicMock(allow=AsyncMock(return_value=True)),
    )
    prompt = service.build_prompt(decision)
    text = await MockExplanationProvider().generate(prompt, 500)
    assert "WAIT" in text
    assert "XAUUSD" in text
