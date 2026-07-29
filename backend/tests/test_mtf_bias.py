"""MTF bias rule tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from atlas.domain.models.enums import Bias, Timeframe, Trend
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.price_level import PriceLevel
from atlas.domain.models.smc import SMCAnalysisResult, StructureBreak
from atlas.domain.models.technical import TechnicalAnalysisResult
from atlas.domain.services.mtf_bias import (
    bias_from_smc,
    compute_timeframe_bias,
    extract_key_levels,
)


def _instrument() -> Instrument:
    return Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )


def _bars(count: int) -> list[OHLCVBar]:
    instrument = _instrument()
    start = datetime(2026, 1, 1, tzinfo=UTC)
    bars = []
    highs = [10, 11, 15, 12, 11, 13, 18, 14, 13, 16, 22, 17, 16, 20, 26]
    lows = [5, 6, 7, 6, 5, 7, 9, 8, 7, 9, 11, 10, 9, 12, 14]
    for i in range(count):
        h = Decimal(highs[i % len(highs)])
        low = Decimal(lows[i % len(lows)])
        bars.append(
            OHLCVBar(
                instrument=instrument,
                timeframe=Timeframe.H4,
                open_time=start + timedelta(hours=4 * i),
                open=(h + low) / 2,
                high=h,
                low=low,
                close=(h + low) / 2,
                volume=Decimal("100"),
            )
        )
    return bars


def test_smc_uptrend_bias() -> None:
    bars = _bars(60)
    instrument = bars[0].instrument
    smc = SMCAnalysisResult(
        instrument=instrument,
        timeframe=Timeframe.H4,
        trend=Trend.UPTREND,
        last_bos=StructureBreak("bos", Bias.BULLISH, 50, Decimal("2360")),
        last_choch=None,
        order_blocks=(),
        liquidity_pools=(),
        fair_value_gaps=(),
        directional_bias=Bias.BULLISH,
        computed_at=datetime.now(UTC),
    )
    assert bias_from_smc(smc, bars) == Bias.BULLISH


def test_smc_uptrend_neutral_on_recent_bearish_choch() -> None:
    bars = _bars(60)
    instrument = bars[0].instrument
    smc = SMCAnalysisResult(
        instrument=instrument,
        timeframe=Timeframe.H4,
        trend=Trend.UPTREND,
        last_bos=None,
        last_choch=StructureBreak("choch", Bias.BEARISH, 58, Decimal("2340")),
        order_blocks=(),
        liquidity_pools=(),
        fair_value_gaps=(),
        directional_bias=Bias.BEARISH,
        computed_at=datetime.now(UTC),
    )
    assert bias_from_smc(smc, bars) == Bias.NEUTRAL


def test_swing_fallback_when_smc_missing() -> None:
    bars = _bars(60)
    result = compute_timeframe_bias(
        Timeframe.H4,
        bars,
        None,
        None,
        bias_source="smc_trend",
    )
    assert result.trend_source == "swing_structure"
    assert result.bias == Bias.BULLISH


def test_key_levels_filtered_by_strength() -> None:
    instrument = _instrument()
    technical = TechnicalAnalysisResult(
        instrument=instrument,
        timeframe=Timeframe.H4,
        trend=Trend.RANGING,
        key_levels=(
            PriceLevel(Decimal("2350"), Decimal("0.8"), "support"),
            PriceLevel(Decimal("2360"), Decimal("0.4"), "resistance"),
            PriceLevel(Decimal("2370"), Decimal("0.6"), "resistance"),
        ),
        nearest_support=Decimal("2350"),
        nearest_resistance=Decimal("2370"),
        indicator_context={},
        bullish_context_score=Decimal("0"),
        bearish_context_score=Decimal("0"),
        computed_at=datetime.now(UTC),
    )
    levels = extract_key_levels(technical)
    assert len(levels) == 2
    assert all(level.strength >= Decimal("0.5") for level in levels)
