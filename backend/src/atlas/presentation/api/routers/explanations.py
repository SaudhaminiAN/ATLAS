"""AI explanation REST endpoints (Spec 15)."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from atlas.application.ai.service import DecisionNotFoundError, ExplanationRateLimitError
from atlas.domain.models.explanation import DecisionExplanation
from atlas.presentation.api.dtos.explanation import DecisionExplanationDTO
from atlas.presentation.api.schemas import ApiEnvelope, ApiError

router = APIRouter(prefix="/explanations", tags=["explanations"])


def _to_dto(explanation: DecisionExplanation) -> DecisionExplanationDTO:
    return DecisionExplanationDTO(
        id=str(explanation.id),
        decision_id=str(explanation.decision_id),
        content=explanation.content,
        provider=explanation.provider,
        created_at=explanation.created_at,
    )


@router.get("/{decision_id}")
async def get_explanation(
    request: Request, decision_id: UUID
) -> ApiEnvelope[DecisionExplanationDTO]:
    """Return stored explanation for a decision, if any."""
    service = request.app.state.container.ai_explanation_service
    explanation = await service.get_explanation(decision_id)
    if explanation is None:
        return ApiEnvelope(
            success=False,
            data=None,
            error=ApiError(code="NOT_FOUND", message="No explanation for this decision"),
        )
    return ApiEnvelope(success=True, data=_to_dto(explanation))


@router.post("/{decision_id}")
async def generate_explanation(
    request: Request, decision_id: UUID
) -> ApiEnvelope[DecisionExplanationDTO]:
    """Generate (or return cached) natural-language explanation."""
    service = request.app.state.container.ai_explanation_service
    if not service.enabled:
        raise HTTPException(status_code=503, detail="AI explanations are disabled")
    try:
        explanation = await service.explain(decision_id)
    except DecisionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Decision not found") from exc
    except ExplanationRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    if explanation is None:
        raise HTTPException(
            status_code=502,
            detail="Explanation generation failed",
        )
    return ApiEnvelope(success=True, data=_to_dto(explanation))
