"""Analysis pipeline orchestrator (Spec 20)."""

import asyncio
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from atlas.application.confluence.service import ConfluenceService
from atlas.application.decision.service import DecisionEngineService
from atlas.application.market_context.service import MarketContextService
from atlas.application.market_data.service import MarketDataService
from atlas.application.mtf.service import MultiTimeframeAnalysisService
from atlas.application.news.service import NewsFilterService
from atlas.application.price_action.service import PriceActionService
from atlas.application.risk.service import RiskManagementService
from atlas.application.smc.service import SmartMoneyConceptsService
from atlas.application.strategy.service import StrategyEngineService
from atlas.application.technical.service import TechnicalAnalysisService
from atlas.application.validation.service import TradeValidationService
from atlas.domain.events.base import DomainEvent
from atlas.domain.models.backtest import BacktestConfig
from atlas.domain.models.decision import TradingDecision, wait_decision
from atlas.domain.models.enums import Bias, Direction, Timeframe, Trend
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.pipeline import PipelineRun, PipelineStatus, StageResult
from atlas.domain.models.price_action import PriceActionResult
from atlas.domain.models.smc import SMCAnalysisResult
from atlas.domain.models.strategy import StrategyProfile
from atlas.domain.models.technical import TechnicalAnalysisResult
from atlas.domain.models.validation import ValidationContext
from atlas.domain.ports.event_bus import EventBusProtocol
from atlas.infrastructure.cache.pipeline_dedupe import PipelineDedupeCache
from atlas.infrastructure.persistence.repositories import PipelineRunRepository
from atlas.infrastructure.persistence.risk_serializers import risk_result_to_dict

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ReplayOptions:
    """Controls side effects when replaying historical bars (Spec 16)."""

    skip_dedupe: bool = True
    persist_pipeline: bool = False
    persist_decisions: bool = False
    publish_events: bool = False


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    """Pipeline settings from Spec 20."""

    primary_timeframe: Timeframe = Timeframe.M15
    risk_enabled: bool = False
    stage_timeout_seconds: float = 5.0
    dedupe_window_seconds: int = 60


def _neutral_technical(instrument: Instrument, timeframe: Timeframe) -> TechnicalAnalysisResult:
    from decimal import Decimal

    return TechnicalAnalysisResult(
        instrument=instrument,
        timeframe=timeframe,
        trend=Trend.RANGING,
        key_levels=(),
        nearest_support=None,
        nearest_resistance=None,
        indicator_context={},
        bullish_context_score=Decimal("0"),
        bearish_context_score=Decimal("0"),
        computed_at=datetime.now(UTC),
    )


def _neutral_smc(instrument: Instrument, timeframe: Timeframe) -> SMCAnalysisResult:
    return SMCAnalysisResult(
        instrument=instrument,
        timeframe=timeframe,
        trend=Trend.RANGING,
        last_bos=None,
        last_choch=None,
        order_blocks=(),
        liquidity_pools=(),
        fair_value_gaps=(),
        directional_bias=Bias.NEUTRAL,
        computed_at=datetime.now(UTC),
    )


def _empty_price_action(instrument: Instrument, timeframe: Timeframe) -> PriceActionResult:
    return PriceActionResult(
        instrument=instrument,
        timeframe=timeframe,
        patterns=(),
        strongest_pattern=None,
        computed_at=datetime.now(UTC),
    )


@dataclass
class AnalysisPipelineOrchestrator:
    """Orchestrate end-to-end analysis on each primary timeframe bar close."""

    market_data_service: MarketDataService
    market_context_service: MarketContextService
    mtf_service: MultiTimeframeAnalysisService
    technical_analysis_service: TechnicalAnalysisService
    smc_service: SmartMoneyConceptsService
    price_action_service: PriceActionService
    news_filter: NewsFilterService
    confluence_service: ConfluenceService
    trade_validation_service: TradeValidationService
    decision_engine: DecisionEngineService
    strategy_engine: StrategyEngineService
    risk_management_service: RiskManagementService
    dedupe_cache: PipelineDedupeCache
    event_bus: EventBusProtocol
    session_factory: async_sessionmaker[AsyncSession] | None = None
    config: PipelineConfig = field(default_factory=PipelineConfig)

    STAGES: tuple[str, ...] = (
        "market_context",
        "mtf_analysis",
        "technical_analysis",
        "smc_analysis",
        "price_action",
        "news_filter",
        "confluence",
        "validation",
        "risk",
        "decision_engine",
    )

    async def run(
        self,
        instrument: Instrument,
        trigger_bar: OHLCVBar,
        correlation_id: str | None = None,
        *,
        replay: ReplayOptions | None = None,
    ) -> PipelineRun:
        """Execute the full analysis pipeline for a closed bar."""
        cid = correlation_id or str(uuid4())
        started = datetime.now(UTC)
        run = PipelineRun(
            correlation_id=cid,
            instrument=instrument,
            trigger_timeframe=trigger_bar.timeframe,
            trigger_bar_time=trigger_bar.open_time,
            status=PipelineStatus.RUNNING,
            started_at=started,
        )

        if trigger_bar.timeframe != self.config.primary_timeframe:
            run.status = PipelineStatus.SKIPPED
            run.completed_at = datetime.now(UTC)
            return run

        if replay is None or not replay.skip_dedupe:
            acquired = await self.dedupe_cache.try_acquire(
                instrument.symbol,
                trigger_bar.timeframe,
                trigger_bar.open_time,
            )
            if not acquired:
                logger.info(
                    "pipeline_dedupe_skip",
                    correlation_id=cid,
                    symbol=instrument.symbol,
                    open_time=trigger_bar.open_time.isoformat(),
                )
                run.status = PipelineStatus.SKIPPED
                run.completed_at = datetime.now(UTC)
                return run

        logger.info(
            "pipeline_started",
            correlation_id=cid,
            symbol=instrument.symbol,
            open_time=trigger_bar.open_time.isoformat(),
        )

        as_of = trigger_bar.open_time
        strategy = await self.strategy_engine.get_active()
        if not strategy:
            return await self._abort_with_wait(
                run,
                instrument,
                "No active strategy profile",
                started,
                strategy_id="unknown",
                replay=replay,
            )

        try:
            decision = await self._execute_stages(
                run,
                instrument,
                trigger_bar,
                strategy,
                as_of=as_of,
                correlation_id=cid,
                replay=replay,
            )
        except Exception as exc:
            logger.exception("pipeline_failed", correlation_id=cid)
            decision = wait_decision(
                instrument,
                f"Pipeline error: {exc}",
                correlation_id=cid,
                strategy_id=strategy.id,
                decided_at=as_of,
            )
            await self.decision_engine.emit(
                decision,
                persist=replay is None or replay.persist_decisions,
                publish=replay is None or replay.publish_events,
            )
            run.decision_id = decision.id
            run.status = PipelineStatus.FAILED
            run.completed_at = datetime.now(UTC)
            run.duration_ms = int((run.completed_at - started).total_seconds() * 1000)
            if replay is None or replay.publish_events:
                self._publish_failed(run, str(exc))
            if replay is None or replay.persist_pipeline:
                await self._persist_run(run)
            return run

        run.decision_id = decision.id
        run.status = PipelineStatus.COMPLETED
        run.completed_at = datetime.now(UTC)
        run.duration_ms = int((run.completed_at - started).total_seconds() * 1000)
        if replay is None or replay.publish_events:
            self._publish_completed(run, decision)
        if replay is None or replay.persist_pipeline:
            await self._persist_run(run)
        logger.info("pipeline_completed", correlation_id=cid, direction=decision.direction.value)
        return run

    async def _execute_stages(
        self,
        run: PipelineRun,
        instrument: Instrument,
        trigger_bar: OHLCVBar,
        strategy: StrategyProfile,
        *,
        as_of: datetime,
        correlation_id: str,
        replay: ReplayOptions | None = None,
    ) -> TradingDecision:
        context = await self._run_critical_stage(
            run,
            "market_context",
            self.market_context_service.analyze_symbol(
                instrument.symbol,
                as_of=as_of,
                publish_event=False,
            ),
        )
        mtf = await self._run_critical_stage(
            run,
            "mtf_analysis",
            self.mtf_service.analyze_symbol(
                instrument.symbol,
                as_of=as_of,
                publish_event=False,
            ),
        )

        technical_result, smc_result = await asyncio.gather(
            self._run_optional_stage(
                run,
                "technical_analysis",
                self.technical_analysis_service.analyze_symbol(
                    instrument.symbol,
                    timeframe=self.config.primary_timeframe,
                    as_of=as_of,
                    publish_event=False,
                ),
            ),
            self._run_optional_stage(
                run,
                "smc_analysis",
                self.smc_service.analyze_symbol(
                    instrument.symbol,
                    timeframe=self.config.primary_timeframe,
                    as_of=as_of,
                    publish_event=False,
                ),
            ),
        )
        technical = technical_result or _neutral_technical(
            instrument, self.config.primary_timeframe
        )
        smc = smc_result or _neutral_smc(instrument, self.config.primary_timeframe)

        bars = await self.market_data_service.get_recent_bars(
            instrument,
            self.config.primary_timeframe,
            limit=self.price_action_service.config.bar_lookback,
            as_of=as_of,
        )
        price_action = await self._run_optional_stage(
            run,
            "price_action",
            self._analyze_price_action(instrument, bars, technical, smc, as_of),
        )
        price_action = price_action or _empty_price_action(
            instrument, self.config.primary_timeframe
        )

        news_status = await self._run_critical_stage(
            run,
            "news_filter",
            asyncio.to_thread(self.news_filter.check, as_of),
        )

        confluence = await self._run_critical_stage(
            run,
            "confluence",
            asyncio.to_thread(
                self.confluence_service.calculate,
                instrument,
                mtf,
                technical,
                smc,
                price_action,
                context,
                news_status,
                strategy,
                computed_at=as_of,
            ),
        )

        validation = await self._run_critical_stage(
            run,
            "validation",
            asyncio.to_thread(
                self.trade_validation_service.validate,
                ValidationContext(
                    confluence=confluence,
                    mtf=mtf,
                    context=context,
                    technical=technical,
                    smc=smc,
                    news=news_status,
                    strategy=strategy,
                    trigger_bar=trigger_bar,
                ),
            ),
        )

        risk_within_limits = None
        risk_snapshot = None

        if self.config.risk_enabled:
            if (
                validation.is_valid
                and confluence.suggested_direction in (Direction.BUY, Direction.SELL)
            ):
                profile = await self.risk_management_service.get_profile()
                risk_result = await self._run_critical_stage(
                    run,
                    "risk",
                    asyncio.to_thread(
                        self.risk_management_service.calculate,
                        confluence.suggested_direction,
                        trigger_bar.close,
                        technical,
                        smc,
                        context.atr_value,
                        instrument,
                        profile,
                    ),
                )
                risk_snapshot = risk_result_to_dict(risk_result)
                risk_within_limits = risk_result.within_limits
            else:
                run.stage_results["risk"] = StageResult(
                    stage_name="risk",
                    status="skipped",
                    error="Not actionable for risk sizing",
                )
        else:
            run.stage_results["risk"] = StageResult(stage_name="risk", status="skipped")

        decision = await self._run_critical_stage(
            run,
            "decision_engine",
            self._emit_decision(
                confluence,
                validation,
                news_status,
                strategy,
                correlation_id=correlation_id,
                replay=replay,
                risk_within_limits=risk_within_limits,
                risk_snapshot=risk_snapshot,
            ),
        )
        return decision

    async def _emit_decision(
        self,
        confluence,
        validation,
        news_status,
        strategy: StrategyProfile,
        *,
        correlation_id: str,
        replay: ReplayOptions | None = None,
        risk_within_limits: bool | None = None,
        risk_snapshot: dict | None = None,
    ) -> TradingDecision:
        decision = self.decision_engine.resolve(
            confluence,
            validation,
            news_status,
            strategy,
            correlation_id=correlation_id,
            risk_within_limits=risk_within_limits,
        )
        if risk_snapshot is not None:
            decision = replace(decision, risk_snapshot=risk_snapshot)
        await self.decision_engine.emit(
            decision,
            persist=replay is None or replay.persist_decisions,
            publish=replay is None or replay.publish_events,
        )
        return decision

    async def _analyze_price_action(
        self,
        instrument: Instrument,
        bars: list[OHLCVBar],
        technical: TechnicalAnalysisResult,
        smc: SMCAnalysisResult,
        as_of: datetime,
    ) -> PriceActionResult:
        filtered = [bar for bar in bars if bar.open_time <= as_of]
        return self.price_action_service.analyze(
            instrument,
            self.config.primary_timeframe,
            filtered,
            list(technical.key_levels),
            smc,
            computed_at=as_of,
        )

    async def _run_critical_stage(
        self,
        run: PipelineRun,
        stage_name: str,
        awaitable: Any,
    ) -> Any:
        start = time.perf_counter()
        try:
            result = await asyncio.wait_for(
                awaitable,
                timeout=self.config.stage_timeout_seconds,
            )
        except Exception as exc:
            duration_ms = int((time.perf_counter() - start) * 1000)
            run.stage_results[stage_name] = StageResult(
                stage_name=stage_name,
                status="failed",
                duration_ms=duration_ms,
                error=str(exc),
            )
            raise
        if result is None:
            duration_ms = int((time.perf_counter() - start) * 1000)
            run.stage_results[stage_name] = StageResult(
                stage_name=stage_name,
                status="failed",
                duration_ms=duration_ms,
                error="Stage returned no result",
            )
            raise RuntimeError(f"{stage_name} returned no result")
        duration_ms = int((time.perf_counter() - start) * 1000)
        run.stage_results[stage_name] = StageResult(
            stage_name=stage_name,
            status="completed",
            duration_ms=duration_ms,
        )
        return result

    async def _run_optional_stage(
        self,
        run: PipelineRun,
        stage_name: str,
        awaitable: Any,
    ) -> Any:
        start = time.perf_counter()
        try:
            result = await asyncio.wait_for(
                awaitable,
                timeout=self.config.stage_timeout_seconds,
            )
        except Exception as exc:
            duration_ms = int((time.perf_counter() - start) * 1000)
            run.stage_results[stage_name] = StageResult(
                stage_name=stage_name,
                status="warning",
                duration_ms=duration_ms,
                error=str(exc),
            )
            logger.warning(
                "pipeline_stage_warning",
                stage=stage_name,
                error=str(exc),
                correlation_id=run.correlation_id,
            )
            return None
        duration_ms = int((time.perf_counter() - start) * 1000)
        status = "completed" if result is not None else "warning"
        run.stage_results[stage_name] = StageResult(
            stage_name=stage_name,
            status=status,
            duration_ms=duration_ms,
            error=None if result is not None else "Stage returned no result",
        )
        return result

    async def _abort_with_wait(
        self,
        run: PipelineRun,
        instrument: Instrument,
        reason: str,
        started: datetime,
        *,
        stage_name: str = "decision_engine",
        strategy_id: str,
        replay: ReplayOptions | None = None,
    ) -> PipelineRun:
        run.stage_results[stage_name] = StageResult(
            stage_name=stage_name,
            status="failed",
            error=reason,
        )
        decision = wait_decision(
            instrument,
            reason,
            correlation_id=run.correlation_id,
            strategy_id=strategy_id,
            decided_at=run.trigger_bar_time,
        )
        await self.decision_engine.emit(
            decision,
            persist=replay is None or replay.persist_decisions,
            publish=replay is None or replay.publish_events,
        )
        run.decision_id = decision.id
        run.status = PipelineStatus.FAILED
        run.completed_at = datetime.now(UTC)
        run.duration_ms = int((run.completed_at - started).total_seconds() * 1000)
        if replay is None or replay.publish_events:
            self._publish_failed(run, reason)
        if replay is None or replay.persist_pipeline:
            await self._persist_run(run)
        return run

    async def _persist_run(self, run: PipelineRun) -> None:
        if self.session_factory is None:
            return
        if run.status not in (PipelineStatus.COMPLETED, PipelineStatus.FAILED):
            return
        async with self.session_factory() as session:
            await PipelineRunRepository(session).insert(run)

    def _publish_completed(self, run: PipelineRun, decision: TradingDecision) -> None:
        self.event_bus.publish(
            DomainEvent(
                event_type="pipeline.completed",
                correlation_id=run.correlation_id,
                payload={
                    "status": run.status.value,
                    "symbol": run.instrument.symbol if run.instrument else None,
                    "direction": decision.direction.value,
                    "is_actionable": decision.is_actionable,
                    "decision_id": str(decision.id),
                    "stages": {
                        name: result.status for name, result in run.stage_results.items()
                    },
                    "duration_ms": run.duration_ms,
                },
            )
        )

    def _publish_failed(self, run: PipelineRun, reason: str) -> None:
        self.event_bus.publish(
            DomainEvent(
                event_type="pipeline.failed",
                correlation_id=run.correlation_id,
                payload={
                    "status": run.status.value,
                    "reason": reason,
                    "stages": {
                        name: result.status for name, result in run.stage_results.items()
                    },
                },
            )
        )

    async def run_replay(
        self,
        instrument: Instrument,
        bar_iterator: AsyncIterator[OHLCVBar],
        config: BacktestConfig,
    ) -> list[PipelineRun]:
        """Replay pipeline over a historical bar iterator (Spec 16)."""
        replay_opts = ReplayOptions(
            skip_dedupe=True,
            persist_pipeline=config.persist_pipeline_runs,
            persist_decisions=config.persist_decisions,
            publish_events=False,
        )
        prior_risk = self.config.risk_enabled
        if config.risk_enabled != prior_risk:
            self.config = PipelineConfig(
                primary_timeframe=self.config.primary_timeframe,
                risk_enabled=config.risk_enabled,
                stage_timeout_seconds=self.config.stage_timeout_seconds,
                dedupe_window_seconds=self.config.dedupe_window_seconds,
            )
        runs: list[PipelineRun] = []
        try:
            async for bar in bar_iterator:
                if bar.timeframe != config.timeframe:
                    continue
                runs.append(
                    await self.run(
                        instrument,
                        bar,
                        correlation_id=f"replay-{instrument.symbol}-{bar.open_time.isoformat()}",
                        replay=replay_opts,
                    )
                )
        finally:
            if config.risk_enabled != prior_risk:
                self.config = PipelineConfig(
                    primary_timeframe=self.config.primary_timeframe,
                    risk_enabled=prior_risk,
                    stage_timeout_seconds=self.config.stage_timeout_seconds,
                    dedupe_window_seconds=self.config.dedupe_window_seconds,
                )
        return runs
