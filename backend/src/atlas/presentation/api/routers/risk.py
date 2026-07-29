"""Risk management REST endpoints (Spec 10)."""

from dataclasses import replace

from fastapi import APIRouter, HTTPException, Request

from atlas.domain.models.risk import RiskProfile
from atlas.presentation.api.dtos.risk import RiskProfileDTO, UpdateRiskProfileRequest
from atlas.presentation.api.schemas import ApiEnvelope

router = APIRouter(prefix="/risk", tags=["risk"])


def _to_dto(profile: RiskProfile) -> RiskProfileDTO:
    return RiskProfileDTO(
        id=profile.id,
        account_balance=profile.account_balance,
        max_risk_percent=profile.max_risk_percent,
        max_daily_loss_percent=profile.max_daily_loss_percent,
        max_open_positions=profile.max_open_positions,
        min_rr=profile.min_rr,
        buffer_atr_multiplier=profile.buffer_atr_multiplier,
        max_sl_distance_atr=profile.max_sl_distance_atr,
        min_sl_pips=profile.min_sl_pips,
        min_lot=profile.min_lot,
        lot_step=profile.lot_step,
        updated_at=profile.updated_at,
    )


def _apply_updates(profile: RiskProfile, body: UpdateRiskProfileRequest) -> RiskProfile:
    updates: dict = {}
    for field_name in (
        "account_balance",
        "max_risk_percent",
        "max_daily_loss_percent",
        "max_open_positions",
        "min_rr",
        "buffer_atr_multiplier",
        "max_sl_distance_atr",
        "min_sl_pips",
        "min_lot",
        "lot_step",
    ):
        value = getattr(body, field_name)
        if value is not None:
            updates[field_name] = value
    return replace(profile, **updates)


@router.get("/profile")
async def get_risk_profile(request: Request) -> ApiEnvelope[RiskProfileDTO]:
    """Return the active risk profile."""
    service = request.app.state.container.risk_management_service
    try:
        profile = await service.get_profile()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiEnvelope(success=True, data=_to_dto(profile))


@router.put("/profile")
async def update_risk_profile(
    request: Request,
    body: UpdateRiskProfileRequest,
) -> ApiEnvelope[RiskProfileDTO]:
    """Update risk profile settings."""
    service = request.app.state.container.risk_management_service
    try:
        current = await service.get_profile()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    profile = _apply_updates(current, body)
    updated = await service.update_profile(profile)
    return ApiEnvelope(success=True, data=_to_dto(updated))
