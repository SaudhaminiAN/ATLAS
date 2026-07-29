"""Pure position management rules (Spec 12)."""

from decimal import Decimal

from atlas.domain.models.enums import Direction
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.position_management import (
    ActionType,
    PositionAction,
    PositionManagementConfig,
    PositionState,
    PositionStatus,
)


def _entry_price(state: PositionState) -> Decimal:
    return state.entry_price


def _pnl_per_unit(direction: Direction, entry: Decimal, price: Decimal) -> Decimal:
    if direction == Direction.BUY:
        return price - entry
    return entry - price


def _check_close(
    state: PositionState, bar: OHLCVBar
) -> PositionAction | None:
    """SL/TP hit detection; SL wins on same bar."""
    sl = state.current_sl
    tp = state.current_tp
    entry = _entry_price(state)

    if state.direction == Direction.BUY:
        sl_hit = bar.low <= sl
        tp_hit = bar.high >= tp
        if sl_hit and tp_hit:
            if bar.open <= sl:
                price, reason = bar.open, "sl_gap"
            else:
                price, reason = sl, "sl_hit"
        elif sl_hit:
            price = bar.open if bar.open <= sl else sl
            reason = "sl_gap" if bar.open <= sl else "sl_hit"
        elif tp_hit:
            price = bar.open if bar.open >= tp else tp
            reason = "tp_hit"
        else:
            return None
    else:
        sl_hit = bar.high >= sl
        tp_hit = bar.low <= tp
        if sl_hit and tp_hit:
            if bar.open >= sl:
                price, reason = bar.open, "sl_gap"
            else:
                price, reason = sl, "sl_hit"
        elif sl_hit:
            price = bar.open if bar.open >= sl else sl
            reason = "sl_gap" if bar.open >= sl else "sl_hit"
        elif tp_hit:
            price = bar.open if bar.open <= tp else tp
            reason = "tp_hit"
        else:
            return None

    leg_pnl = state.remaining_size * _pnl_per_unit(state.direction, entry, price)
    return PositionAction(
        trade_id=state.trade_id,
        action_type=ActionType.CLOSE,
        old_sl=sl,
        new_sl=None,
        closed_size=state.remaining_size,
        close_price=price,
        reason=reason,
        bar_time=bar.open_time,
        realized_pnl_delta=leg_pnl,
    )


def _check_breakeven(
    state: PositionState, bar: OHLCVBar, config: PositionManagementConfig
) -> PositionAction | None:
    if state.breakeven_applied:
        return None
    entry = _entry_price(state)
    trigger = config.breakeven_at_r * state.risk_distance
    if state.direction == Direction.BUY:
        if bar.high < entry + trigger:
            return None
    else:
        if bar.low > entry - trigger:
            return None
    return PositionAction(
        trade_id=state.trade_id,
        action_type=ActionType.BREAKEVEN,
        old_sl=state.current_sl,
        new_sl=entry,
        closed_size=None,
        close_price=None,
        reason="breakeven",
        bar_time=bar.open_time,
    )


def _check_trailing_atr(
    state: PositionState,
    bar: OHLCVBar,
    atr: Decimal,
    config: PositionManagementConfig,
) -> PositionAction | None:
    if not state.breakeven_applied or not config.trailing_enabled:
        return None
    if config.trailing_method != "atr":
        return None
    offset = config.trailing_atr_multiplier * atr
    if state.direction == Direction.BUY:
        new_sl = bar.close - offset
        if new_sl <= state.current_sl:
            return None
    else:
        new_sl = bar.close + offset
        if new_sl >= state.current_sl:
            return None
    return PositionAction(
        trade_id=state.trade_id,
        action_type=ActionType.TRAIL_SL,
        old_sl=state.current_sl,
        new_sl=new_sl,
        closed_size=None,
        close_price=None,
        reason="trail_atr",
        bar_time=bar.open_time,
    )


def _check_partial(
    state: PositionState, bar: OHLCVBar, config: PositionManagementConfig
) -> PositionAction | None:
    if state.partial_exit_applied or not config.partial_exit_enabled:
        return None
    entry = _entry_price(state)
    target = config.partial_exit_at_r * state.risk_distance
    if state.direction == Direction.BUY:
        if bar.high < entry + target:
            return None
        close_price = entry + target
    else:
        if bar.low > entry - target:
            return None
        close_price = entry - target
    close_size = state.position_size * (config.partial_exit_percent / Decimal("100"))
    if close_size <= Decimal("0"):
        return None
    leg_pnl = close_size * _pnl_per_unit(state.direction, entry, close_price)
    return PositionAction(
        trade_id=state.trade_id,
        action_type=ActionType.PARTIAL_CLOSE,
        old_sl=state.current_sl,
        new_sl=None,
        closed_size=close_size,
        close_price=close_price,
        reason="partial_exit",
        bar_time=bar.open_time,
        realized_pnl_delta=leg_pnl,
    )


def apply_action(
    state: PositionState,
    action: PositionAction,
    config: PositionManagementConfig,
    min_lot: Decimal,
) -> PositionState:
    """Return updated state after applying a single action."""
    if action.action_type == ActionType.CLOSE:
        total_pnl = state.partial_realized_pnl + (action.realized_pnl_delta or Decimal("0"))
        return PositionState(
            trade_id=state.trade_id,
            direction=state.direction,
            entry_price=state.entry_price,
            initial_stop_loss=state.initial_stop_loss,
            current_sl=state.current_sl,
            current_tp=state.current_tp,
            position_size=state.position_size,
            remaining_size=Decimal("0"),
            partial_realized_pnl=total_pnl,
            breakeven_applied=state.breakeven_applied,
            partial_exit_applied=state.partial_exit_applied,
            status=PositionStatus.CLOSED,
        )

    if action.action_type == ActionType.BREAKEVEN:
        assert action.new_sl is not None
        return PositionState(
            trade_id=state.trade_id,
            direction=state.direction,
            entry_price=state.entry_price,
            initial_stop_loss=state.initial_stop_loss,
            current_sl=action.new_sl,
            current_tp=state.current_tp,
            position_size=state.position_size,
            remaining_size=state.remaining_size,
            partial_realized_pnl=state.partial_realized_pnl,
            breakeven_applied=True,
            partial_exit_applied=state.partial_exit_applied,
            status=state.status,
        )

    if action.action_type == ActionType.TRAIL_SL:
        assert action.new_sl is not None
        return PositionState(
            trade_id=state.trade_id,
            direction=state.direction,
            entry_price=state.entry_price,
            initial_stop_loss=state.initial_stop_loss,
            current_sl=action.new_sl,
            current_tp=state.current_tp,
            position_size=state.position_size,
            remaining_size=state.remaining_size,
            partial_realized_pnl=state.partial_realized_pnl,
            breakeven_applied=state.breakeven_applied,
            partial_exit_applied=state.partial_exit_applied,
            status=state.status,
        )

    if action.action_type == ActionType.PARTIAL_CLOSE:
        assert action.closed_size is not None
        remaining = state.remaining_size - action.closed_size
        partial_pnl = state.partial_realized_pnl + (action.realized_pnl_delta or Decimal("0"))
        entry = _entry_price(state)
        if remaining < min_lot:
            # Close entire remainder at partial price
            assert action.close_price is not None
            final_leg = remaining * _pnl_per_unit(state.direction, entry, action.close_price)
            return PositionState(
                trade_id=state.trade_id,
                direction=state.direction,
                entry_price=state.entry_price,
                initial_stop_loss=state.initial_stop_loss,
                current_sl=state.current_sl,
                current_tp=state.current_tp,
                position_size=state.position_size,
                remaining_size=Decimal("0"),
                partial_realized_pnl=partial_pnl + final_leg,
                breakeven_applied=state.breakeven_applied,
                partial_exit_applied=True,
                status=PositionStatus.CLOSED,
            )
        tp2_offset = config.tp2_at_r * state.risk_distance
        if state.direction == Direction.BUY:
            new_tp = entry + tp2_offset
        else:
            new_tp = entry - tp2_offset
        return PositionState(
            trade_id=state.trade_id,
            direction=state.direction,
            entry_price=state.entry_price,
            initial_stop_loss=state.initial_stop_loss,
            current_sl=state.current_sl,
            current_tp=new_tp,
            position_size=state.position_size,
            remaining_size=remaining,
            partial_realized_pnl=partial_pnl,
            breakeven_applied=state.breakeven_applied,
            partial_exit_applied=True,
            status=PositionStatus.PARTIAL,
        )

    return state


def evaluate_bar(
    state: PositionState,
    bar: OHLCVBar,
    atr: Decimal | None,
    config: PositionManagementConfig,
) -> tuple[PositionState, list[PositionAction]]:
    """Evaluate management rules for one bar; returns final state and actions."""
    actions: list[PositionAction] = []
    current = state

    close_action = _check_close(current, bar)
    if close_action:
        actions.append(close_action)
        return apply_action(current, close_action, config, config.min_lot), actions

    be = _check_breakeven(current, bar, config)
    if be:
        actions.append(be)
        current = apply_action(current, be, config, config.min_lot)

    if atr is not None:
        trail = _check_trailing_atr(current, bar, atr, config)
        if trail:
            actions.append(trail)
            current = apply_action(current, trail, config, config.min_lot)

    partial = _check_partial(current, bar, config)
    if partial:
        actions.append(partial)
        current = apply_action(current, partial, config, config.min_lot)

    return current, actions


def manual_close_action(
    state: PositionState, bar: OHLCVBar, reason: str = "manual"
) -> tuple[PositionState, PositionAction]:
    """Close at bar close price (manual exit)."""
    price = bar.close
    leg_pnl = state.remaining_size * _pnl_per_unit(state.direction, _entry_price(state), price)
    action = PositionAction(
        trade_id=state.trade_id,
        action_type=ActionType.CLOSE,
        old_sl=state.current_sl,
        new_sl=None,
        closed_size=state.remaining_size,
        close_price=price,
        reason=reason,
        bar_time=bar.open_time,
        realized_pnl_delta=leg_pnl,
    )
    updated = apply_action(state, action, PositionManagementConfig(
        breakeven_at_r=Decimal("1"),
        trailing_enabled=False,
        trailing_method="atr",
        trailing_atr_multiplier=Decimal("1.5"),
        partial_exit_enabled=False,
        partial_exit_percent=Decimal("50"),
        partial_exit_at_r=Decimal("1.5"),
        tp2_at_r=Decimal("3"),
        min_lot=Decimal("0.01"),
    ), Decimal("0.01"))
    return updated, action
