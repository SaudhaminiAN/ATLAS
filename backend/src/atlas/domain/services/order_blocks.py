"""Order block detection (Spec 06)."""

from decimal import Decimal

from atlas.domain.models.enums import Bias
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.smc import OrderBlock
from atlas.domain.services.bar_validation import compute_atr


def _body_size(bar: OHLCVBar) -> Decimal:
    return abs(bar.close - bar.open)


def _is_bullish(bar: OHLCVBar) -> bool:
    return bar.close > bar.open


def _is_bearish(bar: OHLCVBar) -> bool:
    return bar.close < bar.open


def _zone(bar: OHLCVBar) -> tuple[Decimal, Decimal]:
    return min(bar.open, bar.close), max(bar.open, bar.close)


def _is_mitigated(
    zone_low: Decimal,
    zone_high: Decimal,
    bars_after: list[OHLCVBar],
    mitigation_pct: Decimal,
) -> bool:
    midpoint = zone_low + (zone_high - zone_low) * mitigation_pct
    for bar in bars_after:
        if bar.low <= midpoint <= bar.high:
            return True
    return False


def detect_order_blocks(
    bars: list[OHLCVBar],
    *,
    displacement_atr_multiplier: Decimal = Decimal("1.5"),
    ob_mitigation_pct: Decimal = Decimal("0.50"),
    atr_period: int = 14,
    max_blocks: int = 5,
) -> list[OrderBlock]:
    """Detect unmitigated order blocks from displacement candles."""
    if len(bars) < atr_period + 2:
        return []

    blocks: list[OrderBlock] = []

    for i in range(1, len(bars)):
        atr = compute_atr(bars[: i + 1], atr_period)
        if atr is None or atr <= 0:
            continue

        body = _body_size(bars[i])
        if body == 0 or body < displacement_atr_multiplier * atr:
            continue

        opposing_index = i - 1
        while opposing_index >= 0:
            candidate = bars[opposing_index]
            if _is_bullish(bars[i]) and _is_bearish(candidate):
                zone_low, zone_high = _zone(candidate)
                mitigated = _is_mitigated(
                    zone_low, zone_high, bars[i + 1 :], ob_mitigation_pct
                )
                if not mitigated:
                    blocks.append(
                        OrderBlock(
                            direction=Bias.BULLISH,
                            bar_index=opposing_index,
                            zone_low=zone_low,
                            zone_high=zone_high,
                            is_mitigated=False,
                        )
                    )
                break
            if _is_bearish(bars[i]) and _is_bullish(candidate):
                zone_low, zone_high = _zone(candidate)
                mitigated = _is_mitigated(
                    zone_low, zone_high, bars[i + 1 :], ob_mitigation_pct
                )
                if not mitigated:
                    blocks.append(
                        OrderBlock(
                            direction=Bias.BEARISH,
                            bar_index=opposing_index,
                            zone_low=zone_low,
                            zone_high=zone_high,
                            is_mitigated=False,
                        )
                    )
                break
            opposing_index -= 1

    return blocks[-max_blocks:]
