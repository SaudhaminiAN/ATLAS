"""Strategy engine REST endpoints."""

from fastapi import APIRouter, HTTPException, Request

from atlas.application.strategy.service import ProfileNotFoundError, ProfileValidationError
from atlas.domain.models.strategy import StrategyProfile
from atlas.presentation.api.dtos.strategy import SetActiveProfileRequest, StrategyProfileDTO
from atlas.presentation.api.schemas import ApiEnvelope, ApiError

router = APIRouter(prefix="/strategy", tags=["strategy"])


def _to_dto(profile: StrategyProfile) -> StrategyProfileDTO:
    return StrategyProfileDTO(
        id=profile.id,
        name=profile.name,
        min_confluence_score=profile.min_confluence_score,
        enabled_directions=[d.value for d in profile.enabled_directions],
        confluence_weights=profile.confluence_weights,
        active_timeframes=[tf.value for tf in profile.active_timeframes],
        allowed_sessions=[s.value for s in profile.allowed_sessions],
        validation_rule_flags=profile.validation_rule_flags,
        is_active=profile.is_active,
        updated_at=profile.updated_at,
    )


@router.get("/profiles")
async def list_profiles(request: Request) -> ApiEnvelope[list[StrategyProfileDTO]]:
    """List all strategy profiles."""
    service = request.app.state.container.strategy_engine
    profiles = await service.list_profiles()
    return ApiEnvelope(success=True, data=[_to_dto(p) for p in profiles])


@router.get("/active")
async def get_active_profile(request: Request) -> ApiEnvelope[StrategyProfileDTO]:
    """Return the active strategy profile."""
    service = request.app.state.container.strategy_engine
    profile = await service.get_active()
    return ApiEnvelope(success=True, data=_to_dto(profile))


@router.put("/active")
async def set_active_profile(
    request: Request,
    body: SetActiveProfileRequest,
) -> ApiEnvelope[StrategyProfileDTO]:
    """Switch the active strategy profile."""
    service = request.app.state.container.strategy_engine
    try:
        profile = await service.set_active(body.profile_id)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProfileValidationError as exc:
        return ApiEnvelope(
            success=False,
            data=None,
            error=ApiError(
                code="VALIDATION_ERROR",
                message="Invalid strategy profile",
                details=exc.errors,
            ),
        )
    return ApiEnvelope(success=True, data=_to_dto(profile))
