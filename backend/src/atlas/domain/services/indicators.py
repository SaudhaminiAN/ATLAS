"""Technical indicators (EMA, RSI, ATR) — Spec 05."""

from decimal import Decimal

from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.services.bar_validation import compute_atr


def compute_ema(bars: list[OHLCVBar], period: int) -> Decimal | None:
    """Compute EMA for the given period; None if insufficient bars."""
    if len(bars) < period:
        return None

    multiplier = Decimal(2) / Decimal(period + 1)
    ema = sum(bar.close for bar in bars[:period]) / Decimal(period)
    for bar in bars[period:]:
        ema = (bar.close - ema) * multiplier + ema
    return ema


def compute_rsi(bars: list[OHLCVBar], period: int = 14) -> Decimal | None:
    """Compute RSI(period) from close prices."""
    if len(bars) < period + 1:
        return None

    gains: list[Decimal] = []
    losses: list[Decimal] = []
    for i in range(1, len(bars)):
        change = bars[i].close - bars[i - 1].close
        if change > 0:
            gains.append(change)
            losses.append(Decimal(0))
        elif change < 0:
            gains.append(Decimal(0))
            losses.append(abs(change))
        else:
            gains.append(Decimal(0))
            losses.append(Decimal(0))

    window_gains = gains[-period:]
    window_losses = losses[-period:]
    avg_gain = sum(window_gains) / Decimal(period)
    avg_loss = sum(window_losses) / Decimal(period)

    if avg_loss == 0:
        return Decimal("100")

    rs = avg_gain / avg_loss
    return Decimal("100") - (Decimal("100") / (Decimal(1) + rs))


def price_vs_ema(close: Decimal, ema: Decimal | None) -> Decimal:
    """Return +1, 0, or -1 for close relative to EMA."""
    if ema is None:
        return Decimal(0)
    if close > ema:
        return Decimal(1)
    if close < ema:
        return Decimal(-1)
    return Decimal(0)


def build_indicator_context(bars: list[OHLCVBar]) -> dict[str, Decimal]:
    """Build indicator context dict for the latest bar."""
    close = bars[-1].close
    ema20 = compute_ema(bars, 20)
    ema50 = compute_ema(bars, 50)
    ema200 = compute_ema(bars, 200) if len(bars) >= 200 else None
    rsi = compute_rsi(bars, 14)
    atr = compute_atr(bars, 14)

    context: dict[str, Decimal] = {
        "price_vs_ema20": price_vs_ema(close, ema20),
        "close": close,
    }
    if ema20 is not None:
        context["ema20"] = ema20
    if ema50 is not None:
        context["ema50"] = ema50
    if ema200 is not None:
        context["ema200"] = ema200
    if rsi is not None:
        context["rsi14"] = rsi.quantize(Decimal("0.01"))
    if atr is not None:
        context["atr14"] = atr
    return context
