"""Serialize decision snapshots for JSONB storage."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from atlas.domain.models.confluence import ConfluenceResult, EvidenceItem, ModuleScore
from atlas.domain.models.enums import Bias, Direction
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.news import NewsFilterStatus, NextEventInfo
from atlas.domain.models.validation import ValidationResult, ValidationRuleResult

if TYPE_CHECKING:
    from atlas.domain.models.decision import TradingDecision


def _decimal_str(value: Decimal) -> str:
    return str(value)


def confluence_to_dict(result: ConfluenceResult) -> dict:
    """Serialize confluence result for JSONB."""
    return {
        "symbol": result.instrument.symbol,
        "suggested_direction": result.suggested_direction.value,
        "total_score": _decimal_str(result.total_score),
        "raw_score": _decimal_str(result.raw_score),
        "bullish_raw": _decimal_str(result.bullish_raw),
        "bearish_raw": _decimal_str(result.bearish_raw),
        "news_penalty": _decimal_str(result.news_penalty),
        "module_scores": [
            {
                "source": item.source,
                "direction": item.direction.value,
                "score": _decimal_str(item.score),
                "weight": _decimal_str(item.weight),
                "weighted_contribution": _decimal_str(item.weighted_contribution),
            }
            for item in result.module_scores
        ],
        "evidence": [
            {
                "source": item.source,
                "direction": item.direction.value,
                "weight": _decimal_str(item.weight),
                "score": _decimal_str(item.score),
                "weighted_contribution": _decimal_str(item.weighted_contribution),
                "description": item.description,
            }
            for item in result.evidence
        ],
        "evidence_count": result.evidence_count,
        "has_conflict": result.has_conflict,
        "strategy_profile_id": result.strategy_profile_id,
        "computed_at": result.computed_at.isoformat(),
    }


def validation_to_dict(result: ValidationResult) -> dict:
    """Serialize validation result for JSONB."""
    return {
        "symbol": result.instrument.symbol,
        "direction": result.direction.value,
        "is_valid": result.is_valid,
        "rules": [
            {
                "rule_name": rule.rule_name,
                "passed": rule.passed,
                "reason": rule.reason,
                "enabled": rule.enabled,
            }
            for rule in result.rules
        ],
        "failed_rules": list(result.failed_rules),
        "strategy_profile_id": result.strategy_profile_id,
        "validated_at": result.validated_at.isoformat(),
    }


def news_status_to_dict(status: NewsFilterStatus) -> dict:
    """Serialize news filter status for JSONB."""
    next_event = None
    if status.next_event is not None:
        next_event = {
            "name": status.next_event.name,
            "scheduled_at": status.next_event.scheduled_at.isoformat(),
        }
    return {
        "is_blocked": status.is_blocked,
        "is_soft_downgrade": status.is_soft_downgrade,
        "confluence_penalty": _decimal_str(status.confluence_penalty),
        "next_event": next_event,
        "as_of": status.as_of.isoformat(),
    }


def confluence_from_dict(data: dict, instrument: Instrument) -> ConfluenceResult:
    """Deserialize confluence snapshot."""
    return ConfluenceResult(
        instrument=instrument,
        suggested_direction=Direction(data["suggested_direction"]),
        total_score=Decimal(data["total_score"]),
        raw_score=Decimal(data["raw_score"]),
        bullish_raw=Decimal(data["bullish_raw"]),
        bearish_raw=Decimal(data["bearish_raw"]),
        news_penalty=Decimal(data["news_penalty"]),
        module_scores=tuple(
            ModuleScore(
                source=item["source"],
                direction=Bias(item["direction"]),
                score=Decimal(item["score"]),
                weight=Decimal(item["weight"]),
                weighted_contribution=Decimal(item["weighted_contribution"]),
            )
            for item in data.get("module_scores", [])
        ),
        evidence=tuple(
            EvidenceItem(
                source=item["source"],
                direction=Direction(item["direction"]),
                weight=Decimal(item["weight"]),
                score=Decimal(item["score"]),
                weighted_contribution=Decimal(item["weighted_contribution"]),
                description=item["description"],
            )
            for item in data.get("evidence", [])
        ),
        evidence_count=data["evidence_count"],
        has_conflict=data["has_conflict"],
        strategy_profile_id=data["strategy_profile_id"],
        computed_at=datetime.fromisoformat(data["computed_at"]),
    )


def validation_from_dict(data: dict, instrument: Instrument) -> ValidationResult:
    """Deserialize validation snapshot."""
    return ValidationResult(
        instrument=instrument,
        direction=Direction(data["direction"]),
        is_valid=data["is_valid"],
        rules=tuple(
            ValidationRuleResult(
                rule_name=rule["rule_name"],
                passed=rule["passed"],
                reason=rule["reason"],
                enabled=rule["enabled"],
            )
            for rule in data.get("rules", [])
        ),
        failed_rules=tuple(data.get("failed_rules", [])),
        strategy_profile_id=data["strategy_profile_id"],
        validated_at=datetime.fromisoformat(data["validated_at"]),
    )


def news_status_from_dict(data: dict) -> NewsFilterStatus:
    """Deserialize news status snapshot."""
    next_event = None
    raw_next = data.get("next_event")
    if raw_next:
        next_event = NextEventInfo(
            name=raw_next["name"],
            scheduled_at=datetime.fromisoformat(raw_next["scheduled_at"]),
        )
    return NewsFilterStatus(
        is_blocked=data["is_blocked"],
        is_soft_downgrade=data["is_soft_downgrade"],
        confluence_penalty=Decimal(data["confluence_penalty"]),
        next_event=next_event,
        as_of=datetime.fromisoformat(data["as_of"]),
    )


def decision_to_cache_dict(decision: TradingDecision) -> dict:
    """Serialize decision for Redis cache."""
    payload: dict = {
        "id": str(decision.id),
        "instrument_id": str(decision.instrument.id),
        "symbol": decision.instrument.symbol,
        "direction": decision.direction.value,
        "is_actionable": decision.is_actionable,
        "confluence_score": _decimal_str(decision.confluence_score),
        "strategy_id": decision.strategy_id,
        "reason": decision.reason,
        "correlation_id": decision.correlation_id,
        "decided_at": decision.decided_at.isoformat(),
        "confluence_snapshot": (
            confluence_to_dict(decision.confluence_snapshot)
            if decision.confluence_snapshot
            else None
        ),
        "validation_snapshot": (
            validation_to_dict(decision.validation_snapshot)
            if decision.validation_snapshot
            else None
        ),
        "risk_snapshot": decision.risk_snapshot,
        "news_status": (
            news_status_to_dict(decision.news_status) if decision.news_status else None
        ),
    }
    return payload
