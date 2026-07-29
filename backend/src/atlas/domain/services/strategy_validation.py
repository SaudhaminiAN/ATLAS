"""Strategy profile configuration validation."""

from decimal import Decimal, InvalidOperation

from atlas.domain.models.enums import Direction, Timeframe, TradingSession
from atlas.domain.models.strategy import KNOWN_VALIDATION_RULES

WEIGHT_SUM_TOLERANCE = Decimal("0.01")


def validate_profile_config(config: dict) -> list[str]:
    """Validate profile config dict; return human-readable error messages."""
    errors: list[str] = []

    min_score = config.get("min_confluence_score")
    if min_score is None:
        errors.append("min_confluence_score is required")
    else:
        try:
            score = Decimal(str(min_score))
            if score < Decimal("0") or score > Decimal("1"):
                errors.append("min_confluence_score must be between 0.0 and 1.0")
        except (InvalidOperation, TypeError):
            errors.append("min_confluence_score must be a number")

    directions = config.get("enabled_directions")
    if not directions:
        errors.append("enabled_directions must be non-empty")
    else:
        for d in directions:
            try:
                parsed = Direction(str(d))
            except ValueError:
                errors.append(f"unknown direction: {d}")
                continue
            if parsed == Direction.WAIT:
                errors.append("enabled_directions cannot include WAIT")

    weights = config.get("confluence_weights")
    if not weights or not isinstance(weights, dict):
        errors.append("confluence_weights must be a non-empty object")
    else:
        try:
            total = sum(Decimal(str(v)) for v in weights.values())
            if abs(total - Decimal("1")) > WEIGHT_SUM_TOLERANCE:
                errors.append(
                    f"confluence_weights must sum to 1.0 ± {WEIGHT_SUM_TOLERANCE} (got {total})"
                )
        except (InvalidOperation, TypeError):
            errors.append("confluence_weights values must be numeric")

    timeframes = config.get("active_timeframes")
    if not timeframes or len(timeframes) < 2:
        errors.append("active_timeframes must contain at least 2 entries")
    else:
        for tf in timeframes:
            try:
                Timeframe(str(tf))
            except ValueError:
                errors.append(f"unknown timeframe: {tf}")

    sessions = config.get("allowed_sessions")
    if not sessions:
        errors.append("allowed_sessions must be non-empty")
    else:
        for session in sessions:
            try:
                TradingSession(str(session))
            except ValueError:
                errors.append(f"unknown session: {session}")

    rules = config.get("validation_rules")
    if not rules or not isinstance(rules, dict):
        errors.append("validation_rules must be a non-empty object")
    else:
        unknown = set(rules.keys()) - KNOWN_VALIDATION_RULES
        if unknown:
            errors.append(f"unknown validation rule(s): {', '.join(sorted(unknown))}")
        if not any(bool(v) for v in rules.values()):
            errors.append("at least one validation rule must be enabled")

    return errors
