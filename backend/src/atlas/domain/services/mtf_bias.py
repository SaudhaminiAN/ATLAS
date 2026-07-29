"""MTF per-timeframe bias rules (Spec 04)."""

from decimal import Decimal

from atlas.domain.models.enums import Bias, Timeframe, Trend
from atlas.domain.models.mtf import TimeframeBias
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.price_level import PriceLevel
from atlas.domain.models.smc import SMCAnalysisResult
from atlas.domain.models.technical import TechnicalAnalysisResult
from atlas.domain.services.structural_bias import compute_structural_bias

CHOCH_LOOKBACK_BARS = 10
KEY_LEVEL_MIN_STRENGTH = Decimal("0.5")
KEY_LEVEL_MAX_COUNT = 3


def extract_key_levels(technical: TechnicalAnalysisResult | None) -> tuple[PriceLevel, ...]:
    """Top 3 key levels with strength >= 0.5 from technical analysis."""
    if not technical:
        return ()
    qualifying = [
        level
        for level in technical.key_levels
        if level.strength >= KEY_LEVEL_MIN_STRENGTH
    ]
    qualifying.sort(key=lambda level: level.strength, reverse=True)
    return tuple(qualifying[:KEY_LEVEL_MAX_COUNT])


def _choch_in_last_bars(smc: SMCAnalysisResult, bars: list[OHLCVBar], direction: Bias) -> bool:
    if not smc.last_choch or smc.last_choch.direction != direction:
        return False
    return smc.last_choch.bar_index >= len(bars) - CHOCH_LOOKBACK_BARS


def bias_from_smc(smc: SMCAnalysisResult, bars: list[OHLCVBar]) -> Bias:
    """Method A: SMC trend with recent CHoCH filter."""
    if smc.trend == Trend.UPTREND and not _choch_in_last_bars(smc, bars, Bias.BEARISH):
        return Bias.BULLISH
    if smc.trend == Trend.DOWNTREND and not _choch_in_last_bars(smc, bars, Bias.BULLISH):
        return Bias.BEARISH
    return Bias.NEUTRAL


def confidence_from_smc(smc: SMCAnalysisResult, bias: Bias) -> Decimal:
    """Per-TF confidence based on BOS agreement."""
    if bias == Bias.NEUTRAL:
        return Decimal("0.3")
    if smc.last_bos and smc.last_bos.direction == bias:
        return Decimal("1.0")
    return Decimal("0.6")


def compute_timeframe_bias(
    timeframe: Timeframe,
    bars: list[OHLCVBar],
    smc: SMCAnalysisResult | None,
    technical: TechnicalAnalysisResult | None,
    *,
    bias_source: str = "smc_trend",
    swing_lookback: int = 2,
    min_bars: int = 50,
) -> TimeframeBias:
    """Compute bias for one timeframe using SMC or swing fallback."""
    key_levels = extract_key_levels(technical)

    if len(bars) < min_bars:
        return TimeframeBias(
            timeframe=timeframe,
            bias=Bias.NEUTRAL,
            confidence=Decimal("0.3"),
            trend_source="insufficient_data",
            key_levels=key_levels,
        )

    if smc is not None and bias_source == "smc_trend":
        bias = bias_from_smc(smc, bars)
        confidence = confidence_from_smc(smc, bias)
        trend_source = "smc_trend"
    else:
        bias = compute_structural_bias(bars, swing_lookback=swing_lookback)
        confidence = Decimal("0.6") if bias != Bias.NEUTRAL else Decimal("0.3")
        trend_source = "swing_structure"

    return TimeframeBias(
        timeframe=timeframe,
        bias=bias,
        confidence=confidence,
        trend_source=trend_source,
        key_levels=key_levels,
    )
