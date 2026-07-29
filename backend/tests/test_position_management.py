"""Unit tests for position management rules (Spec 12)."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from atlas.domain.models.enums import Direction, Timeframe
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.position_management import (
    ActionType,
    PositionManagementConfig,
    PositionState,
    PositionStatus,
)
from atlas.domain.services.position_management import evaluate_bar


def _instrument() -> Instrument:
    return Instrument(
        id=uuid4(),
        symbol="XAUUSD",
        display_name="Gold",
        pip_size=Decimal("0.01"),
        lot_size=Decimal("100"),
    )


def _bar(
    *,
    open_: Decimal,
    high: Decimal,
    low: Decimal,
    close: Decimal,
    open_time: datetime | None = None,
) -> OHLCVBar:
    return OHLCVBar(
        instrument=_instrument(),
        timeframe=Timeframe.M15,
        open_time=open_time or datetime(2025, 1, 1, 12, 0, tzinfo=UTC),
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=Decimal("100"),
    )


def _config(**overrides) -> PositionManagementConfig:
    defaults = dict(
        breakeven_at_r=Decimal("1.0"),
        trailing_enabled=True,
        trailing_method="atr",
        trailing_atr_multiplier=Decimal("1.5"),
        partial_exit_enabled=True,
        partial_exit_percent=Decimal("50"),
        partial_exit_at_r=Decimal("1.5"),
        tp2_at_r=Decimal("3.0"),
        min_lot=Decimal("0.01"),
    )
    defaults.update(overrides)
    return PositionManagementConfig(**defaults)


def _buy_state(**overrides) -> PositionState:
    defaults = dict(
        trade_id=uuid4(),
        direction=Direction.BUY,
        entry_price=Decimal("2350"),
        initial_stop_loss=Decimal("2340"),
        current_sl=Decimal("2340"),
        current_tp=Decimal("2370"),
        position_size=Decimal("0.10"),
        remaining_size=Decimal("0.10"),
        partial_realized_pnl=Decimal("0"),
        breakeven_applied=False,
        partial_exit_applied=False,
        status=PositionStatus.OPEN,
    )
    defaults.update(overrides)
    return PositionState(**defaults)


def test_breakeven_moves_sl_once() -> None:
    state = _buy_state()
    bar = _bar(open_=Decimal("2355"), high=Decimal("2361"), low=Decimal("2354"), close=Decimal("2360"))
    new_state, actions = evaluate_bar(state, bar, Decimal("5"), _config(trailing_enabled=False))
    assert len(actions) == 1
    assert actions[0].action_type == ActionType.BREAKEVEN
    assert new_state.current_sl == Decimal("2350")
    assert new_state.breakeven_applied is True


def test_breakeven_not_retriggered() -> None:
    state = _buy_state(breakeven_applied=True, current_sl=Decimal("2350"))
    bar = _bar(open_=Decimal("2360"), high=Decimal("2365"), low=Decimal("2359"), close=Decimal("2364"))
    _, actions = evaluate_bar(state, bar, Decimal("5"), _config())
    assert not any(a.action_type == ActionType.BREAKEVEN for a in actions)


def test_trailing_only_tightens_sl() -> None:
    state = _buy_state(breakeven_applied=True, current_sl=Decimal("2350"))
    bar = _bar(open_=Decimal("2362"), high=Decimal("2368"), low=Decimal("2361"), close=Decimal("2366"))
    new_state, actions = evaluate_bar(state, bar, Decimal("4"), _config())
    trail = [a for a in actions if a.action_type == ActionType.TRAIL_SL]
    assert len(trail) == 1
    assert new_state.current_sl == Decimal("2360")  # 2366 - 1.5*4


def test_trailing_rejects_wider_sl() -> None:
    state = _buy_state(breakeven_applied=True, current_sl=Decimal("2360"))
    bar = _bar(open_=Decimal("2361"), high=Decimal("2362"), low=Decimal("2359"), close=Decimal("2360"))
    new_state, actions = evaluate_bar(state, bar, Decimal("4"), _config())
    assert not any(a.action_type == ActionType.TRAIL_SL for a in actions)
    assert new_state.current_sl == Decimal("2360")


def test_partial_exit_reduces_size() -> None:
    state = _buy_state()
    # 1.5R from 2350 with 10 risk = 2365
    bar = _bar(open_=Decimal("2360"), high=Decimal("2366"), low=Decimal("2359"), close=Decimal("2365"))
    new_state, actions = evaluate_bar(state, bar, None, _config(partial_exit_enabled=True))
    partial = [a for a in actions if a.action_type == ActionType.PARTIAL_CLOSE]
    assert len(partial) == 1
    assert new_state.remaining_size == Decimal("0.05")
    assert new_state.partial_exit_applied is True
    assert new_state.current_tp == Decimal("2380")  # 3R


def test_sl_hit_closes_buy() -> None:
    state = _buy_state()
    bar = _bar(open_=Decimal("2345"), high=Decimal("2346"), low=Decimal("2338"), close=Decimal("2339"))
    new_state, actions = evaluate_bar(state, bar, None, _config())
    assert len(actions) == 1
    assert actions[0].action_type == ActionType.CLOSE
    assert actions[0].reason == "sl_hit"
    assert new_state.status == PositionStatus.CLOSED
    assert new_state.partial_realized_pnl == Decimal("-1.0")


def test_same_bar_sl_beats_tp() -> None:
    state = _buy_state()
    bar = _bar(
        open_=Decimal("2368"),
        high=Decimal("2375"),
        low=Decimal("2335"),
        close=Decimal("2340"),
    )
    _, actions = evaluate_bar(state, bar, None, _config())
    assert actions[0].action_type == ActionType.CLOSE
    assert actions[0].reason in ("sl_hit", "sl_gap")


def test_gap_through_sl_closes_at_open() -> None:
    state = _buy_state()
    bar = _bar(open_=Decimal("2335"), high=Decimal("2340"), low=Decimal("2330"), close=Decimal("2338"))
    _, actions = evaluate_bar(state, bar, None, _config())
    assert actions[0].reason == "sl_gap"
    assert actions[0].close_price == Decimal("2335")


def test_integration_breakeven_trail_close() -> None:
    state = _buy_state()
    config = _config()

    bar1 = _bar(open_=Decimal("2355"), high=Decimal("2361"), low=Decimal("2354"), close=Decimal("2360"))
    state, a1 = evaluate_bar(state, bar1, Decimal("4"), config)
    assert a1[0].action_type == ActionType.BREAKEVEN

    bar2 = _bar(open_=Decimal("2362"), high=Decimal("2368"), low=Decimal("2361"), close=Decimal("2367"))
    state, a2 = evaluate_bar(state, bar2, Decimal("4"), config)
    assert any(a.action_type == ActionType.TRAIL_SL for a in a2)

    bar3 = _bar(open_=Decimal("2365"), high=Decimal("2366"), low=Decimal("2348"), close=Decimal("2350"))
    state, a3 = evaluate_bar(state, bar3, Decimal("4"), config)
    assert a3[-1].action_type == ActionType.CLOSE
    assert state.status == PositionStatus.CLOSED
