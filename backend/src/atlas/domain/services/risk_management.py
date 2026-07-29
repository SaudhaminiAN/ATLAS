"""Risk SL/TP/sizing formulas (Spec 10)."""

from decimal import ROUND_DOWN, Decimal

from atlas.domain.models.enums import Bias, Direction
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.risk import RiskCheckResult, RiskParameters, RiskProfile
from atlas.domain.models.smc import SMCAnalysisResult
from atlas.domain.models.technical import TechnicalAnalysisResult


def _nearest_bullish_ob_low(smc: SMCAnalysisResult, entry: Decimal) -> Decimal | None:
    candidates = [
        block.zone_low
        for block in smc.order_blocks
        if block.direction == Bias.BULLISH and not block.is_mitigated and block.zone_low < entry
    ]
    return max(candidates) if candidates else None


def _nearest_bearish_ob_high(smc: SMCAnalysisResult, entry: Decimal) -> Decimal | None:
    candidates = [
        block.zone_high
        for block in smc.order_blocks
        if block.direction == Bias.BEARISH and not block.is_mitigated and block.zone_high > entry
    ]
    return min(candidates) if candidates else None


def _floor_to_step(value: Decimal, step: Decimal) -> Decimal:
    if step <= 0:
        return value
    units = (value / step).quantize(Decimal("1"), rounding=ROUND_DOWN)
    return units * step


def _structural_sl_buy(
    entry: Decimal,
    technical: TechnicalAnalysisResult,
    smc: SMCAnalysisResult,
) -> tuple[Decimal | None, str | None]:
    candidates: list[tuple[Decimal, str]] = []
    if technical.nearest_support is not None and technical.nearest_support < entry:
        candidates.append((technical.nearest_support, "support"))
    ob_low = _nearest_bullish_ob_low(smc, entry)
    if ob_low is not None:
        candidates.append((ob_low, "order_block"))
    if not candidates:
        return None, None
    level, basis = max(candidates, key=lambda item: item[0])
    return level, basis


def _structural_sl_sell(
    entry: Decimal,
    technical: TechnicalAnalysisResult,
    smc: SMCAnalysisResult,
) -> tuple[Decimal | None, str | None]:
    candidates: list[tuple[Decimal, str]] = []
    if technical.nearest_resistance is not None and technical.nearest_resistance > entry:
        candidates.append((technical.nearest_resistance, "resistance"))
    ob_high = _nearest_bearish_ob_high(smc, entry)
    if ob_high is not None:
        candidates.append((ob_high, "order_block"))
    if not candidates:
        return None, None
    level, basis = min(candidates, key=lambda item: item[0])
    return level, basis


def calculate_risk(
    direction: Direction,
    entry_price: Decimal,
    technical: TechnicalAnalysisResult,
    smc: SMCAnalysisResult,
    atr: Decimal,
    instrument: Instrument,
    profile: RiskProfile,
    *,
    open_positions_count: int = 0,
    daily_pnl: Decimal = Decimal("0"),
) -> RiskCheckResult:
    """Compute SL/TP, position size, and enforce account limits."""
    if direction == Direction.WAIT:
        return RiskCheckResult(False, None, "No direction to size")

    max_daily_loss = profile.account_balance * profile.max_daily_loss_percent / Decimal("100")
    if daily_pnl <= -max_daily_loss:
        return RiskCheckResult(False, None, "Max daily loss limit reached")

    if open_positions_count >= profile.max_open_positions:
        return RiskCheckResult(False, None, "Max open positions reached")

    if atr <= 0:
        return RiskCheckResult(False, None, "ATR unavailable")

    if direction == Direction.BUY:
        candidate, sl_basis = _structural_sl_buy(entry_price, technical, smc)
        if candidate is None:
            return RiskCheckResult(False, None, "No structural SL level")
        if entry_price - candidate > profile.max_sl_distance_atr * atr:
            return RiskCheckResult(False, None, "No SL within 3× ATR")
        stop_loss = candidate - profile.buffer_atr_multiplier * atr
    else:
        candidate, sl_basis = _structural_sl_sell(entry_price, technical, smc)
        if candidate is None:
            return RiskCheckResult(False, None, "No structural SL level")
        if candidate - entry_price > profile.max_sl_distance_atr * atr:
            return RiskCheckResult(False, None, "No SL within 3× ATR")
        stop_loss = candidate + profile.buffer_atr_multiplier * atr

    pip_size = instrument.pip_size
    sl_pips = abs(entry_price - stop_loss) / pip_size
    if sl_pips < profile.min_sl_pips:
        return RiskCheckResult(False, None, f"SL distance {sl_pips:.1f} pips below minimum")

    risk_distance = abs(entry_price - stop_loss)
    if direction == Direction.BUY:
        take_profit = entry_price + risk_distance * profile.min_rr
    else:
        take_profit = entry_price - risk_distance * profile.min_rr

    risk_amount = profile.account_balance * profile.max_risk_percent / Decimal("100")
    pip_risk = risk_distance / pip_size
    pip_value_per_lot = pip_size * instrument.lot_size
    if pip_risk <= 0 or pip_value_per_lot <= 0:
        return RiskCheckResult(False, None, "Invalid pip risk")

    raw_size = risk_amount / (pip_risk * pip_value_per_lot)
    position_size = _floor_to_step(raw_size, profile.lot_step)
    if position_size < profile.min_lot:
        return RiskCheckResult(False, None, "Position size below minimum lot")

    params = RiskParameters(
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        position_size=position_size,
        risk_amount=risk_amount,
        reward_risk_ratio=profile.min_rr,
        sl_basis=sl_basis or "unknown",
    )
    return RiskCheckResult(True, params, None)
