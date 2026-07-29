"""Decision REST endpoints."""

from fastapi import APIRouter, Query, Request

from atlas.domain.models.decision import TradingDecision
from atlas.presentation.api.dtos.confluence import ConfluenceDTO, EvidenceItemDTO, ModuleScoreDTO
from atlas.presentation.api.dtos.decision import NewsStatusDTO, TradingDecisionDTO
from atlas.presentation.api.dtos.validation import ValidationResultDTO, ValidationRuleResultDTO
from atlas.presentation.api.schemas import ApiEnvelope, ApiError

router = APIRouter(prefix="/decisions", tags=["decisions"])


def _to_dto(decision: TradingDecision) -> TradingDecisionDTO:
    confluence = None
    if decision.confluence_snapshot is not None:
        snapshot = decision.confluence_snapshot
        confluence = ConfluenceDTO(
            symbol=snapshot.instrument.symbol,
            suggested_direction=snapshot.suggested_direction.value,
            total_score=snapshot.total_score,
            raw_score=snapshot.raw_score,
            bullish_raw=snapshot.bullish_raw,
            bearish_raw=snapshot.bearish_raw,
            news_penalty=snapshot.news_penalty,
            module_scores=[
                ModuleScoreDTO(
                    source=item.source,
                    direction=item.direction.value,
                    score=item.score,
                    weight=item.weight,
                    weighted_contribution=item.weighted_contribution,
                )
                for item in snapshot.module_scores
            ],
            evidence=[
                EvidenceItemDTO(
                    source=item.source,
                    direction=item.direction.value,
                    weight=item.weight,
                    score=item.score,
                    weighted_contribution=item.weighted_contribution,
                    description=item.description,
                )
                for item in snapshot.evidence
            ],
            evidence_count=snapshot.evidence_count,
            has_conflict=snapshot.has_conflict,
            strategy_profile_id=snapshot.strategy_profile_id,
            computed_at=snapshot.computed_at,
        )

    validation = None
    if decision.validation_snapshot is not None:
        snapshot = decision.validation_snapshot
        validation = ValidationResultDTO(
            symbol=snapshot.instrument.symbol,
            direction=snapshot.direction.value,
            is_valid=snapshot.is_valid,
            rules=[
                ValidationRuleResultDTO(
                    rule_name=rule.rule_name,
                    passed=rule.passed,
                    reason=rule.reason,
                    enabled=rule.enabled,
                )
                for rule in snapshot.rules
            ],
            failed_rules=list(snapshot.failed_rules),
            strategy_profile_id=snapshot.strategy_profile_id,
            validated_at=snapshot.validated_at,
        )

    news = None
    if decision.news_status is not None:
        status = decision.news_status
        news = NewsStatusDTO(
            is_blocked=status.is_blocked,
            is_soft_downgrade=status.is_soft_downgrade,
            confluence_penalty=status.confluence_penalty,
            next_event_name=status.next_event.name if status.next_event else None,
            next_event_at=status.next_event.scheduled_at if status.next_event else None,
            as_of=status.as_of,
        )

    return TradingDecisionDTO(
        id=decision.id,
        symbol=decision.instrument.symbol,
        direction=decision.direction.value,
        is_actionable=decision.is_actionable,
        confluence_score=decision.confluence_score,
        strategy_id=decision.strategy_id,
        reason=decision.reason,
        correlation_id=decision.correlation_id,
        decided_at=decision.decided_at,
        confluence_snapshot=confluence,
        validation_snapshot=validation,
        risk_snapshot=decision.risk_snapshot,
        news_status=news,
    )


@router.get("/{symbol}/latest")
async def get_latest_decision(request: Request, symbol: str) -> ApiEnvelope[TradingDecisionDTO]:
    """Latest trading decision for a symbol."""
    service = request.app.state.container.decision_engine
    decision = await service.get_latest(symbol)
    if decision is None:
        return ApiEnvelope(
            success=False,
            data=None,
            error=ApiError(code="NOT_FOUND", message="No decisions found for symbol"),
        )
    return ApiEnvelope(success=True, data=_to_dto(decision))


@router.get("/{symbol}/history")
async def get_decision_history(
    request: Request,
    symbol: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ApiEnvelope[list[TradingDecisionDTO]]:
    """Paginated decision history for a symbol."""
    service = request.app.state.container.decision_engine
    decisions = await service.get_history(symbol, limit=limit, offset=offset)
    return ApiEnvelope(success=True, data=[_to_dto(item) for item in decisions])
