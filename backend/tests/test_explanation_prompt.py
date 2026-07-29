"""Unit tests for explanation prompt builder (Spec 15)."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from atlas.domain.models.confluence import ConfluenceResult, EvidenceItem
from atlas.domain.models.decision import TradingDecision, wait_decision
from atlas.domain.models.enums import Direction
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.news import NewsFilterStatus
from atlas.domain.models.validation import ValidationResult, ValidationRuleResult
from atlas.domain.services.explanation_prompt import (
    SYSTEM_PROMPT,
    build_prompt,
    build_prompt_payload,
    mock_explanation_from_payload,
    validate_guardrails,
)


def _instrument() -> Instrument:
    return Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )


def _confluence() -> ConfluenceResult:
    instrument = _instrument()
    now = datetime.now(UTC)
    evidence = (
        EvidenceItem(
            source="smc_structure",
            direction=Direction.BUY,
            weight=Decimal("0.3"),
            score=Decimal("0.7"),
            weighted_contribution=Decimal("0.21"),
            description="Bullish structure",
        ),
    )
    return ConfluenceResult(
        instrument=instrument,
        suggested_direction=Direction.BUY,
        total_score=Decimal("0.62"),
        raw_score=Decimal("0.65"),
        bullish_raw=Decimal("0.65"),
        bearish_raw=Decimal("0.10"),
        news_penalty=Decimal("0"),
        module_scores=(),
        evidence=evidence,
        evidence_count=1,
        has_conflict=False,
        strategy_profile_id="default",
        computed_at=now,
    )


def test_guardrails_present_in_system_prompt() -> None:
    assert validate_guardrails(SYSTEM_PROMPT)


def test_build_prompt_payload_from_snapshot_only() -> None:
    instrument = _instrument()
    validation = ValidationResult(
        instrument=instrument,
        direction=Direction.BUY,
        is_valid=False,
        rules=(
            ValidationRuleResult(
                rule_name="minimum_rr_potential",
                passed=False,
                reason="RR too low",
                enabled=True,
            ),
        ),
        failed_rules=("minimum_rr_potential",),
        strategy_profile_id="default",
        validated_at=datetime.now(UTC),
    )
    decision = wait_decision(
        instrument,
        "Validation failed: minimum_rr_potential",
        correlation_id="c1",
        strategy_id="default",
        confluence_score=Decimal("0.62"),
        confluence=_confluence(),
        validation=validation,
    )
    payload = build_prompt_payload(decision)
    assert payload["direction"] == "WAIT"
    assert payload["failed_rules"] == ["minimum_rr_potential"]
    assert payload["evidence"][0]["source"] == "smc_structure"


def test_wait_explanation_cites_failed_rules() -> None:
    payload = {
        "symbol": "XAUUSD",
        "direction": "WAIT",
        "reason": "Validation failed",
        "confluence_score": 0.62,
        "failed_rules": ["minimum_rr_potential"],
        "news_blocked": False,
        "evidence": [],
    }
    text = mock_explanation_from_payload(payload)
    assert "minimum_rr_potential" in text
    assert "WAIT" in text


def test_build_prompt_includes_json_block() -> None:
    decision = wait_decision(
        _instrument(),
        "Confluence below threshold",
        correlation_id="c1",
        strategy_id="default",
    )
    prompt = build_prompt(decision)
    assert "Decision data:" in prompt
    assert validate_guardrails(prompt)
