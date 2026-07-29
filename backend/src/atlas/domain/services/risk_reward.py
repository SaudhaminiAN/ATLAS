"""Minimum R:R potential calculation (Spec 09)."""

from decimal import Decimal

from atlas.domain.models.enums import Bias, Direction
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.smc import SMCAnalysisResult
from atlas.domain.models.technical import TechnicalAnalysisResult

MINIMUM_RR = Decimal("2.0")


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


def evaluate_minimum_rr(
    direction: Direction,
    trigger_bar: OHLCVBar,
    technical: TechnicalAnalysisResult,
    smc: SMCAnalysisResult,
    *,
    minimum_rr: Decimal = MINIMUM_RR,
) -> tuple[bool, str]:
    """Return pass/fail and reason for minimum_rr_potential rule."""
    entry = trigger_bar.close

    if direction == Direction.BUY:
        stop_loss = technical.nearest_support or _nearest_bullish_ob_low(smc, entry)
        take_profit = technical.nearest_resistance
        if stop_loss is None or take_profit is None:
            return False, "No structural SL/TP levels"
        risk = entry - stop_loss
        reward = take_profit - entry
    elif direction == Direction.SELL:
        stop_loss = technical.nearest_resistance or _nearest_bearish_ob_high(smc, entry)
        take_profit = technical.nearest_support
        if stop_loss is None or take_profit is None:
            return False, "No structural SL/TP levels"
        risk = stop_loss - entry
        reward = entry - take_profit
    else:
        return False, "No direction to validate"

    if risk <= 0:
        return False, "Invalid risk distance"

    rr = reward / risk
    if rr >= minimum_rr:
        return True, f"R:R {rr:.2f} meets minimum {minimum_rr}"
    return False, f"R:R {rr:.2f} below minimum {minimum_rr}"
