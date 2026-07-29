"""Confluence scoring rules (Spec 08)."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from atlas.domain.models.confluence import ConfluenceResult, EvidenceItem, ModuleScore
from atlas.domain.models.enums import Bias, Direction, VolatilityRegime
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.market_context import MarketContext
from atlas.domain.models.mtf import MTFAnalysis
from atlas.domain.models.news import NewsFilterStatus
from atlas.domain.models.price_action import PriceActionResult
from atlas.domain.models.smc import SMCAnalysisResult
from atlas.domain.models.strategy import StrategyProfile
from atlas.domain.models.technical import TechnicalAnalysisResult

MODULE_SOURCES = (
    "mtf_alignment",
    "smc_structure",
    "price_action",
    "technical_levels",
    "market_context",
)


@dataclass(frozen=True, slots=True)
class DirectionalScore:
    """Normalized module directional score."""

    direction: Bias
    score: Decimal


def score_mtf(mtf: MTFAnalysis) -> DirectionalScore:
    direction = mtf.dominant_bias
    if direction == Bias.NEUTRAL or not mtf.aligned:
        return DirectionalScore(Bias.NEUTRAL, Decimal("0"))
    return DirectionalScore(direction, mtf.alignment_score)


def score_smc(smc: SMCAnalysisResult) -> DirectionalScore:
    direction = smc.directional_bias
    if direction == Bias.NEUTRAL:
        return DirectionalScore(Bias.NEUTRAL, Decimal("0"))
    if smc.last_bos and smc.last_bos.direction == direction:
        return DirectionalScore(direction, Decimal("1.0"))
    if smc.last_choch and smc.last_choch.direction == direction:
        return DirectionalScore(direction, Decimal("0.7"))
    return DirectionalScore(direction, Decimal("0.5"))


def score_price_action(price_action: PriceActionResult) -> DirectionalScore:
    pattern = price_action.strongest_pattern
    if pattern is None:
        return DirectionalScore(Bias.NEUTRAL, Decimal("0"))
    score = pattern.strength
    if pattern.at_key_level:
        score = min(score * Decimal("1.1"), Decimal("1.0"))
    return DirectionalScore(pattern.direction, score)


def score_technical(technical: TechnicalAnalysisResult) -> DirectionalScore:
    if technical.bullish_context_score > technical.bearish_context_score:
        return DirectionalScore(Bias.BULLISH, technical.bullish_context_score)
    if technical.bearish_context_score > technical.bullish_context_score:
        return DirectionalScore(Bias.BEARISH, technical.bearish_context_score)
    return DirectionalScore(Bias.NEUTRAL, Decimal("0"))


def score_market_context(context: MarketContext) -> DirectionalScore:
    direction = context.structural_bias
    if direction in (Bias.BULLISH, Bias.BEARISH):
        score = (
            Decimal("0.8")
            if context.volatility_regime == VolatilityRegime.NORMAL
            else Decimal("0.5")
        )
    else:
        score = Decimal("0")
    if context.volatility_regime == VolatilityRegime.EXTREME:
        score = Decimal("0")
    return DirectionalScore(direction, score)


def _bias_to_direction(bias: Bias) -> Direction:
    if bias == Bias.BULLISH:
        return Direction.BUY
    if bias == Bias.BEARISH:
        return Direction.SELL
    return Direction.WAIT


def _module_description(source: str, directional: DirectionalScore) -> str:
    return f"{source}: {directional.direction.value} score {directional.score}"


def has_directional_conflict(
    module_scores: list[ModuleScore],
    *,
    min_weight: Decimal = Decimal("0.15"),
    min_score: Decimal = Decimal("0.50"),
) -> bool:
    """True when weighted modules disagree with strong opposing scores."""
    bullish = False
    bearish = False
    for module in module_scores:
        if module.weight < min_weight or module.score < min_score:
            continue
        if module.direction == Bias.BULLISH:
            bullish = True
        elif module.direction == Bias.BEARISH:
            bearish = True
    return bullish and bearish


def calculate_confluence(
    instrument: Instrument,
    mtf: MTFAnalysis,
    technical: TechnicalAnalysisResult,
    smc: SMCAnalysisResult,
    price_action: PriceActionResult,
    context: MarketContext,
    news_status: NewsFilterStatus,
    strategy: StrategyProfile,
    *,
    min_evidence_count: int = 3,
    evidence_threshold: Decimal = Decimal("0.30"),
    computed_at: datetime | None = None,
) -> ConfluenceResult:
    """Aggregate module scores into a confluence result."""
    scorers = {
        "mtf_alignment": score_mtf(mtf),
        "smc_structure": score_smc(smc),
        "price_action": score_price_action(price_action),
        "technical_levels": score_technical(technical),
        "market_context": score_market_context(context),
    }

    module_scores: list[ModuleScore] = []
    evidence: list[EvidenceItem] = []
    bullish_raw = Decimal("0")
    bearish_raw = Decimal("0")

    for source in MODULE_SOURCES:
        directional = scorers[source]
        weight = strategy.confluence_weights.get(source, Decimal("0"))
        contribution = Decimal("0")
        if directional.direction == Bias.BULLISH:
            contribution = weight * directional.score
            bullish_raw += contribution
        elif directional.direction == Bias.BEARISH:
            contribution = weight * directional.score
            bearish_raw += contribution

        module_scores.append(
            ModuleScore(
                source=source,
                direction=directional.direction,
                score=directional.score,
                weight=weight,
                weighted_contribution=contribution,
            )
        )

        if directional.score >= evidence_threshold and directional.direction != Bias.NEUTRAL:
            evidence.append(
                EvidenceItem(
                    source=source,
                    direction=_bias_to_direction(directional.direction),
                    weight=weight,
                    score=directional.score,
                    weighted_contribution=contribution,
                    description=_module_description(source, directional),
                )
            )

    evidence_count = len(evidence)
    conflict = has_directional_conflict(module_scores)
    raw_score = max(bullish_raw, bearish_raw)
    penalty = news_status.confluence_penalty
    total_score = max(min(raw_score - penalty, Decimal("1.0")), Decimal("0"))

    if bullish_raw > bearish_raw:
        dominant = Direction.BUY
    elif bearish_raw > bullish_raw:
        dominant = Direction.SELL
    else:
        dominant = Direction.WAIT

    suggested = dominant
    if total_score < strategy.min_confluence_score:
        suggested = Direction.WAIT
    if evidence_count < min_evidence_count:
        suggested = Direction.WAIT
    if conflict:
        suggested = Direction.WAIT

    return ConfluenceResult(
        instrument=instrument,
        suggested_direction=suggested,
        total_score=total_score,
        raw_score=raw_score,
        bullish_raw=bullish_raw,
        bearish_raw=bearish_raw,
        news_penalty=penalty,
        module_scores=tuple(module_scores),
        evidence=tuple(evidence),
        evidence_count=evidence_count,
        has_conflict=conflict,
        strategy_profile_id=strategy.id,
        computed_at=computed_at or news_status.as_of,
    )
