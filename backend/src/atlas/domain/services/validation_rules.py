"""Trade validation rules (Spec 09)."""

from atlas.domain.models.enums import Bias, Direction, SpreadStatus, Timeframe, VolatilityRegime
from atlas.domain.models.mtf import MTFAnalysis
from atlas.domain.models.validation import ValidationContext, ValidationRuleResult
from atlas.domain.services.risk_reward import evaluate_minimum_rr

RULE_NAMES = (
    "mtf_alignment_minimum",
    "confluence_score_minimum",
    "no_counter_trend",
    "minimum_rr_potential",
    "news_block",
    "session_check",
    "spread_check",
    "volatility_check",
)


def _bias_for_timeframe(mtf: MTFAnalysis, timeframe: Timeframe) -> Bias | None:
    for bias in mtf.biases:
        if bias.timeframe == timeframe:
            return bias.bias
    return None


def _evaluate_rule(name: str, context: ValidationContext) -> ValidationRuleResult:
    strategy = context.strategy
    enabled = strategy.is_rule_enabled(name)

    if not enabled:
        return ValidationRuleResult(
            rule_name=name,
            passed=True,
            reason="Rule disabled",
            enabled=False,
        )

    if name == "mtf_alignment_minimum":
        passed = context.mtf.aligned
        reason = "MTF aligned" if passed else "MTF not aligned"
    elif name == "confluence_score_minimum":
        passed = context.confluence.total_score >= strategy.min_confluence_score
        reason = (
            f"Confluence score {context.confluence.total_score} meets minimum"
            if passed
            else (
                f"Confluence score {context.confluence.total_score} below minimum "
                f"{strategy.min_confluence_score}"
            )
        )
    elif name == "no_counter_trend":
        direction = context.confluence.suggested_direction
        d1_bias = _bias_for_timeframe(context.mtf, Timeframe.D1)
        h4_bias = _bias_for_timeframe(context.mtf, Timeframe.H4)
        if direction == Direction.BUY and (
            d1_bias == Bias.BEARISH or h4_bias == Bias.BEARISH
        ):
            passed = False
            reason = "BUY conflicts with D1/H4 bearish bias"
        elif direction == Direction.SELL and (
            d1_bias == Bias.BULLISH or h4_bias == Bias.BULLISH
        ):
            passed = False
            reason = "SELL conflicts with D1/H4 bullish bias"
        else:
            passed = True
            reason = "Direction aligned with higher-timeframe bias"
    elif name == "minimum_rr_potential":
        passed, reason = evaluate_minimum_rr(
            context.confluence.suggested_direction,
            context.trigger_bar,
            context.technical,
            context.smc,
        )
    elif name == "news_block":
        passed = not context.news.is_blocked
        reason = "No active news block" if passed else "High-impact news block active"
    elif name == "session_check":
        passed = context.context.primary_session in strategy.allowed_sessions
        reason = (
            f"Session {context.context.primary_session.value} allowed"
            if passed
            else f"Session {context.context.primary_session.value} not allowed"
        )
    elif name == "spread_check":
        passed = context.context.spread_status != SpreadStatus.ELEVATED
        reason = "Spread normal" if passed else "Spread elevated"
    elif name == "volatility_check":
        passed = context.context.volatility_regime != VolatilityRegime.EXTREME
        reason = (
            "Volatility regime acceptable"
            if passed
            else "Volatility regime extreme"
        )
    else:
        passed = False
        reason = f"Unknown rule: {name}"

    return ValidationRuleResult(
        rule_name=name,
        passed=passed,
        reason=reason,
        enabled=True,
    )


def evaluate_validation_rules(context: ValidationContext) -> list[ValidationRuleResult]:
    """Evaluate all known validation rules."""
    return [_evaluate_rule(name, context) for name in RULE_NAMES]


def validate_context(context: ValidationContext) -> tuple[bool, list[ValidationRuleResult]]:
    """Evaluate rules and return overall validity."""
    direction = context.confluence.suggested_direction
    if direction == Direction.WAIT:
        return False, [
            ValidationRuleResult(
                rule_name="direction_check",
                passed=False,
                reason="No direction to validate",
                enabled=True,
            )
        ]

    results = evaluate_validation_rules(context)
    failed = [result.rule_name for result in results if result.enabled and not result.passed]
    is_valid = not failed
    return is_valid, results
