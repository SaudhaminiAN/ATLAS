"""Risk profile persistence helpers."""

from decimal import Decimal

from atlas.domain.models.risk import RiskCheckResult, RiskParameters, RiskProfile


def risk_profile_from_dict(data: dict) -> RiskProfile:
    from datetime import UTC, datetime

    return RiskProfile(
        id=str(data["id"]),
        account_balance=Decimal(str(data["account_balance"])),
        max_risk_percent=Decimal(str(data["max_risk_percent"])),
        max_daily_loss_percent=Decimal(str(data["max_daily_loss_percent"])),
        max_open_positions=int(data["max_open_positions"]),
        min_rr=Decimal(str(data["min_rr"])),
        buffer_atr_multiplier=Decimal(str(data["buffer_atr_multiplier"])),
        max_sl_distance_atr=Decimal(str(data["max_sl_distance_atr"])),
        min_sl_pips=int(data["min_sl_pips"]),
        min_lot=Decimal(str(data["min_lot"])),
        lot_step=Decimal(str(data["lot_step"])),
        updated_at=data.get("updated_at") or datetime.now(UTC),
    )


def risk_profile_to_dict(profile: RiskProfile) -> dict:
    return {
        "id": profile.id,
        "account_balance": float(profile.account_balance),
        "max_risk_percent": float(profile.max_risk_percent),
        "max_daily_loss_percent": float(profile.max_daily_loss_percent),
        "max_open_positions": profile.max_open_positions,
        "min_rr": float(profile.min_rr),
        "buffer_atr_multiplier": float(profile.buffer_atr_multiplier),
        "max_sl_distance_atr": float(profile.max_sl_distance_atr),
        "min_sl_pips": profile.min_sl_pips,
        "min_lot": float(profile.min_lot),
        "lot_step": float(profile.lot_step),
    }


def risk_result_to_dict(result: RiskCheckResult) -> dict:
    params = result.parameters
    param_dict = None
    if params is not None:
        param_dict = {
            "entry_price": str(params.entry_price),
            "stop_loss": str(params.stop_loss),
            "take_profit": str(params.take_profit),
            "position_size": str(params.position_size),
            "risk_amount": str(params.risk_amount),
            "reward_risk_ratio": str(params.reward_risk_ratio),
            "sl_basis": params.sl_basis,
        }
    return {
        "within_limits": result.within_limits,
        "breach_reason": result.breach_reason,
        "parameters": param_dict,
    }
