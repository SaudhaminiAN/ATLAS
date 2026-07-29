"""Analysis REST endpoints."""

from datetime import datetime

from fastapi import APIRouter, Query, Request

from atlas.domain.models.enums import Timeframe
from atlas.domain.models.market_context import MarketContext
from atlas.domain.models.mtf import MTFAnalysis
from atlas.domain.models.smc import SMCAnalysisResult, StructureBreak
from atlas.domain.models.technical import TechnicalAnalysisResult
from atlas.presentation.api.dtos.market_context import MarketContextDTO
from atlas.presentation.api.dtos.mtf import MTFAnalysisDTO, TimeframeBiasDTO
from atlas.presentation.api.dtos.smc import (
    FairValueGapDTO,
    LiquidityPoolDTO,
    OrderBlockDTO,
    SMCAnalysisDTO,
    StructureBreakDTO,
)
from atlas.presentation.api.dtos.technical import PriceLevelDTO, TechnicalAnalysisDTO
from atlas.presentation.api.schemas import ApiEnvelope, ApiError

router = APIRouter(prefix="/analysis", tags=["analysis"])


def _to_dto(context: MarketContext) -> MarketContextDTO:
    return MarketContextDTO(
        symbol=context.instrument.symbol,
        primary_session=context.primary_session.value,
        active_sessions=[s.value for s in context.active_sessions],
        volatility_regime=context.volatility_regime.value,
        spread_status=context.spread_status.value,
        structural_bias=context.structural_bias.value,
        atr_value=context.atr_value,
        atr_percentile=context.atr_percentile,
        computed_at=context.computed_at,
    )


@router.get("/{symbol}/context")
async def get_market_context(
    request: Request,
    symbol: str,
    as_of: datetime | None = Query(default=None),
    refresh: bool = Query(default=False),
) -> ApiEnvelope[MarketContextDTO]:
    """Current market context snapshot for a symbol."""
    service = request.app.state.container.market_context_service

    if refresh or as_of is not None:
        context = await service.analyze_symbol(symbol, as_of=as_of)
    else:
        context = await service.get_cached(symbol)
        if context is None:
            context = await service.analyze_symbol(symbol)

    if not context:
        return ApiEnvelope(
            success=False,
            data=None,
            error=ApiError(
                code="NOT_FOUND",
                message="Instrument not found or insufficient bar data",
            ),
        )

    return ApiEnvelope(success=True, data=_to_dto(context))


def _mtf_to_dto(analysis: MTFAnalysis) -> MTFAnalysisDTO:
    return MTFAnalysisDTO(
        symbol=analysis.instrument.symbol,
        biases=[
            TimeframeBiasDTO(
                timeframe=b.timeframe.value,
                bias=b.bias.value,
                confidence=b.confidence,
                trend_source=b.trend_source,
                key_levels=[
                    {
                        "price": str(level.price),
                        "strength": str(level.strength),
                        "level_type": level.level_type,
                    }
                    for level in b.key_levels
                ],
            )
            for b in analysis.biases
        ],
        alignment_score=analysis.alignment_score,
        dominant_bias=analysis.dominant_bias.value,
        has_conflict=analysis.has_conflict,
        distant_conflict=analysis.distant_conflict,
        aligned=analysis.aligned,
        computed_at=analysis.computed_at,
    )


@router.get("/{symbol}/mtf")
async def get_mtf_analysis(
    request: Request,
    symbol: str,
    as_of: datetime | None = Query(default=None),
) -> ApiEnvelope[MTFAnalysisDTO]:
    """Multi-timeframe alignment analysis for a symbol."""
    service = request.app.state.container.mtf_service
    analysis = await service.analyze_symbol(symbol, as_of=as_of)

    if not analysis:
        return ApiEnvelope(
            success=False,
            data=None,
            error=ApiError(
                code="NOT_FOUND",
                message="Instrument not found or insufficient bar data",
            ),
        )

    return ApiEnvelope(success=True, data=_mtf_to_dto(analysis))


def _technical_to_dto(result: TechnicalAnalysisResult) -> TechnicalAnalysisDTO:
    return TechnicalAnalysisDTO(
        symbol=result.instrument.symbol,
        timeframe=result.timeframe.value,
        trend=result.trend.value,
        key_levels=[
            PriceLevelDTO(
                price=level.price,
                strength=level.strength,
                level_type=level.level_type,
            )
            for level in result.key_levels
        ],
        nearest_support=result.nearest_support,
        nearest_resistance=result.nearest_resistance,
        indicator_context=result.indicator_context,
        bullish_context_score=result.bullish_context_score,
        bearish_context_score=result.bearish_context_score,
        computed_at=result.computed_at,
    )


@router.get("/{symbol}/technical")
async def get_technical_analysis(
    request: Request,
    symbol: str,
    timeframe: Timeframe = Query(default=Timeframe.M15),
    as_of: datetime | None = Query(default=None),
) -> ApiEnvelope[TechnicalAnalysisDTO]:
    """Technical analysis snapshot for a symbol/timeframe."""
    service = request.app.state.container.technical_analysis_service
    result = await service.analyze_symbol(symbol, timeframe=timeframe, as_of=as_of)

    if not result:
        return ApiEnvelope(
            success=False,
            data=None,
            error=ApiError(
                code="NOT_FOUND",
                message="Instrument not found or insufficient bar data",
            ),
        )

    return ApiEnvelope(success=True, data=_technical_to_dto(result))


def _structure_break_to_dto(break_: StructureBreak) -> StructureBreakDTO:
    return StructureBreakDTO(
        break_type=break_.break_type,
        direction=break_.direction.value,
        bar_index=break_.bar_index,
        price=break_.price,
    )


def _smc_to_dto(result: SMCAnalysisResult) -> SMCAnalysisDTO:
    return SMCAnalysisDTO(
        symbol=result.instrument.symbol,
        timeframe=result.timeframe.value,
        trend=result.trend.value,
        directional_bias=result.directional_bias.value,
        last_bos=_structure_break_to_dto(result.last_bos) if result.last_bos else None,
        last_choch=_structure_break_to_dto(result.last_choch) if result.last_choch else None,
        order_blocks=[
            OrderBlockDTO(
                direction=ob.direction.value,
                bar_index=ob.bar_index,
                zone_low=ob.zone_low,
                zone_high=ob.zone_high,
            )
            for ob in result.order_blocks
        ],
        liquidity_pools=[
            LiquidityPoolDTO(
                pool_type=pool.pool_type,
                price=pool.price,
                touch_count=pool.touch_count,
                strength=pool.strength,
            )
            for pool in result.liquidity_pools
        ],
        fair_value_gaps=[
            FairValueGapDTO(
                direction=gap.direction.value,
                bar_index=gap.bar_index,
                gap_low=gap.gap_low,
                gap_high=gap.gap_high,
            )
            for gap in result.fair_value_gaps
        ],
        computed_at=result.computed_at,
    )


@router.get("/{symbol}/smc")
async def get_smc_analysis(
    request: Request,
    symbol: str,
    timeframe: Timeframe = Query(default=Timeframe.M15),
    as_of: datetime | None = Query(default=None),
) -> ApiEnvelope[SMCAnalysisDTO]:
    """Smart money concepts analysis snapshot for a symbol/timeframe."""
    service = request.app.state.container.smc_service
    result = await service.analyze_symbol(symbol, timeframe=timeframe, as_of=as_of)

    if not result:
        return ApiEnvelope(
            success=False,
            data=None,
            error=ApiError(
                code="NOT_FOUND",
                message="Instrument not found or insufficient bar data",
            ),
        )

    return ApiEnvelope(success=True, data=_smc_to_dto(result))
