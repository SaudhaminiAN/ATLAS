"""Risk management formula tests (Spec 10)."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from atlas.domain.models.enums import Bias, Direction, Timeframe, Trend
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.risk import RiskProfile
from atlas.domain.models.smc import SMCAnalysisResult
from atlas.domain.models.technical import TechnicalAnalysisResult
from atlas.domain.services.risk_management import calculate_risk


def _instrument() -> Instrument:
    return Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )


def _profile() -> RiskProfile:
    return RiskProfile(
        id="default",
        account_balance=Decimal("10000"),
        max_risk_percent=Decimal("1.0"),
        max_daily_loss_percent=Decimal("3.0"),
        max_open_positions=2,
        min_rr=Decimal("2.0"),
        buffer_atr_multiplier=Decimal("0.2"),
        max_sl_distance_atr=Decimal("3.0"),
        min_sl_pips=5,
        min_lot=Decimal("0.01"),
        lot_step=Decimal("0.01"),
        updated_at=datetime.now(UTC),
    )


def _technical(
    *,
    support: Decimal | None,
    resistance: Decimal | None,
) -> TechnicalAnalysisResult:
    return TechnicalAnalysisResult(
        instrument=_instrument(),
        timeframe=Timeframe.M15,
        trend=Trend.UPTREND,
        key_levels=(),
        nearest_support=support,
        nearest_resistance=resistance,
        indicator_context={},
        bullish_context_score=Decimal("0.5"),
        bearish_context_score=Decimal("0.1"),
        computed_at=datetime.now(UTC),
    )


def _smc() -> SMCAnalysisResult:
    return SMCAnalysisResult(
        instrument=_instrument(),
        timeframe=Timeframe.M15,
        trend=Trend.UPTREND,
        last_bos=None,
        last_choch=None,
        order_blocks=(),
        liquidity_pools=(),
        fair_value_gaps=(),
        directional_bias=Bias.BULLISH,
        computed_at=datetime.now(UTC),
    )


def test_buy_risk_calculates_sl_tp_and_size() -> None:
    entry = Decimal("2350")
    support = Decimal("2340")
    atr = Decimal("5")
    result = calculate_risk(
        Direction.BUY,
        entry,
        _technical(support=support, resistance=Decimal("2380")),
        _smc(),
        atr,
        _instrument(),
        _profile(),
    )
    assert result.within_limits is True
    assert result.parameters is not None
    params = result.parameters
    assert params.stop_loss == support - Decimal("0.2") * atr
    risk_distance = entry - params.stop_loss
    assert params.take_profit == entry + risk_distance * Decimal("2.0")
    assert params.risk_amount == Decimal("100")
    assert params.position_size >= Decimal("0.01")


def test_fails_when_sl_too_close() -> None:
    entry = Decimal("2350")
    support = Decimal("2349.98")
    result = calculate_risk(
        Direction.BUY,
        entry,
        _technical(support=support, resistance=Decimal("2380")),
        _smc(),
        Decimal("0.1"),
        _instrument(),
        _profile(),
    )
    assert result.within_limits is False
    assert result.breach_reason is not None
    assert "pips" in result.breach_reason


def test_fails_when_daily_loss_limit_hit() -> None:
    result = calculate_risk(
        Direction.BUY,
        Decimal("2350"),
        _technical(support=Decimal("2340"), resistance=Decimal("2380")),
        _smc(),
        Decimal("5"),
        _instrument(),
        _profile(),
        daily_pnl=Decimal("-400"),
    )
    assert result.within_limits is False
    assert result.breach_reason == "Max daily loss limit reached"


def test_fails_when_no_structural_level() -> None:
    result = calculate_risk(
        Direction.BUY,
        Decimal("2350"),
        _technical(support=None, resistance=None),
        _smc(),
        Decimal("5"),
        _instrument(),
        _profile(),
    )
    assert result.within_limits is False
    assert result.breach_reason == "No structural SL level"
