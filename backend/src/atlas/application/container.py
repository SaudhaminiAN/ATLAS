"""Dependency injection container."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from atlas.application.auth.service import AuthService
from atlas.application.ai.service import AIExplanationService
from atlas.application.analytics.service import AnalyticsService
from atlas.application.backtesting.runner import BacktestRunner
from atlas.application.confluence.service import ConfluenceConfig, ConfluenceService
from atlas.application.decision.service import DecisionEngineService
from atlas.application.execution.service import ExecutionService
from atlas.application.journal.service import JournalService
from atlas.application.market_context.service import MarketContextConfig, MarketContextService
from atlas.application.market_data.service import MarketDataConfig, MarketDataService
from atlas.application.mtf.service import MTFConfig, MultiTimeframeAnalysisService
from atlas.application.news.service import NewsFilterService
from atlas.application.pipeline.orchestrator import AnalysisPipelineOrchestrator, PipelineConfig
from atlas.application.price_action.service import PriceActionConfig, PriceActionService
from atlas.application.smc.service import SmartMoneyConceptsService, SMCConfig
from atlas.application.position_management.service import PositionManagementService
from atlas.application.risk.service import RiskManagementService
from atlas.application.strategy.service import StrategyEngineService
from atlas.application.technical.service import TechnicalAnalysisConfig, TechnicalAnalysisService
from atlas.application.validation.service import TradeValidationConfig, TradeValidationService
from atlas.domain.models.enums import Timeframe
from atlas.domain.models.position_management import PositionManagementConfig
from atlas.domain.ports.event_bus import EventBusProtocol
from atlas.domain.services.news_window import NewsFilterConfig
from atlas.infrastructure.cache.bar_cache import BarCache
from atlas.infrastructure.cache.context_cache import ContextCache
from atlas.infrastructure.cache.decision_cache import DecisionCache
from atlas.infrastructure.cache.execution_idempotency import ExecutionIdempotencyCache
from atlas.infrastructure.cache.explanation_rate_limit import ExplanationRateLimiter
from atlas.infrastructure.cache.news_cache import NewsEventCache
from atlas.infrastructure.cache.pipeline_dedupe import PipelineDedupeCache
from atlas.infrastructure.cache.strategy_cache import StrategyProfileCache
from atlas.infrastructure.config import Settings
from atlas.infrastructure.events.in_memory_bus import InMemoryEventBus
from atlas.infrastructure.execution.paper_provider import PaperExecutionProvider
from atlas.infrastructure.market_data.mock_provider import MockMarketDataProvider
from atlas.infrastructure.market_data.replay import DatabaseMarketDataReplay
from atlas.infrastructure.news.mock_provider import MockNewsCalendarProvider


@dataclass
class Container:
    """Application service container."""

    settings: Settings
    event_bus: EventBusProtocol
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    redis: Redis
    pipeline: AnalysisPipelineOrchestrator
    market_data_service: MarketDataService
    market_data_replay: DatabaseMarketDataReplay
    mock_provider: MockMarketDataProvider
    bar_cache: BarCache
    strategy_engine: StrategyEngineService
    news_filter: NewsFilterService
    market_context_service: MarketContextService
    mtf_service: MultiTimeframeAnalysisService
    technical_analysis_service: TechnicalAnalysisService
    smc_service: SmartMoneyConceptsService
    price_action_service: PriceActionService
    confluence_service: ConfluenceService
    trade_validation_service: TradeValidationService
    decision_engine: DecisionEngineService
    journal_service: JournalService
    backtest_runner: BacktestRunner
    analytics_service: AnalyticsService
    risk_management_service: RiskManagementService
    execution_service: ExecutionService
    position_management_service: PositionManagementService
    ai_explanation_service: AIExplanationService
    auth_service: AuthService


def _build_explanation_provider(settings: Settings):
    if settings.ai_explanation_provider == "openai" and settings.openai_api_key:
        from atlas.infrastructure.ai.openai_provider import OpenAIExplanationProvider

        return OpenAIExplanationProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )
    from atlas.infrastructure.ai.mock_provider import MockExplanationProvider

    return MockExplanationProvider()


def build_container(settings: Settings, engine: AsyncEngine, redis: Redis) -> Container:
    from atlas.infrastructure.persistence.database import create_session_factory

    event_bus = InMemoryEventBus()
    session_factory = create_session_factory(engine)
    bar_cache = BarCache(redis)
    profile_cache = StrategyProfileCache(redis)
    news_cache = NewsEventCache(redis)

    market_data_config = MarketDataConfig(
        outlier_atr_multiplier=Decimal(str(settings.market_data_outlier_atr_multiplier)),
        outlier_atr_lookback=settings.market_data_outlier_atr_lookback,
        gap_tolerance_bars=settings.market_data_gap_tolerance_bars,
    )
    market_data_service = MarketDataService(
        session_factory=session_factory,
        event_bus=event_bus,
        bar_cache=bar_cache,
        config=market_data_config,
    )

    context_cache = ContextCache(redis)
    market_context_service = MarketContextService(
        market_data_service=market_data_service,
        event_bus=event_bus,
        context_cache=context_cache,
        config=MarketContextConfig(
            bias_timeframe=Timeframe(settings.market_context_bias_timeframe),
            primary_timeframe=Timeframe(settings.market_context_primary_timeframe),
            atr_period=settings.market_context_atr_period,
            atr_percentile_lookback=settings.market_context_atr_percentile_lookback,
            min_bars_required=settings.market_context_min_bars_required,
        ),
    )

    strategy_engine = StrategyEngineService(
        session_factory=session_factory,
        event_bus=event_bus,
        profile_cache=profile_cache,
    )

    mtf_service = MultiTimeframeAnalysisService(
        market_data_service=market_data_service,
        strategy_engine=strategy_engine,
        event_bus=event_bus,
        config=MTFConfig(
            alignment_threshold=Decimal(str(settings.mtf_alignment_threshold)),
            bias_source=settings.mtf_bias_source,
            min_bars=settings.mtf_min_bars,
            bar_lookback=settings.mtf_bar_lookback,
        ),
    )

    technical_analysis_service = TechnicalAnalysisService(
        market_data_service=market_data_service,
        event_bus=event_bus,
        config=TechnicalAnalysisConfig(
            swing_lookback=settings.technical_swing_lookback,
            merge_tolerance_pct=Decimal(str(settings.technical_merge_tolerance_pct)),
            min_bars=settings.technical_min_bars,
            bar_lookback=settings.technical_bar_lookback,
        ),
    )

    smc_service = SmartMoneyConceptsService(
        market_data_service=market_data_service,
        event_bus=event_bus,
        config=SMCConfig(
            swing_lookback=settings.smc_swing_lookback,
            displacement_atr_multiplier=Decimal(str(settings.smc_displacement_atr_multiplier)),
            ob_mitigation_pct=Decimal(str(settings.smc_ob_mitigation_pct)),
            equal_level_tolerance_pct=Decimal(str(settings.smc_equal_level_tolerance_pct)),
            fvg_fill_pct=Decimal(str(settings.smc_fvg_fill_pct)),
            min_bars=settings.smc_min_bars,
            bar_lookback=settings.smc_bar_lookback,
        ),
    )

    price_action_service = PriceActionService(
        market_data_service=market_data_service,
        technical_analysis_service=technical_analysis_service,
        smc_service=smc_service,
        event_bus=event_bus,
        config=PriceActionConfig(
            level_proximity_pct=Decimal(str(settings.price_action_level_proximity_pct)),
            min_pattern_strength=Decimal(str(settings.price_action_min_pattern_strength)),
            displacement_atr_multiplier=Decimal(
                str(settings.price_action_displacement_atr_multiplier)
            ),
            min_bars=settings.price_action_min_bars,
            bar_lookback=settings.price_action_bar_lookback,
        ),
    )

    news_filter = NewsFilterService(
        session_factory=session_factory,
        event_bus=event_bus,
        provider=MockNewsCalendarProvider(),
        event_cache=news_cache,
        config=NewsFilterConfig(
            hard_block_minutes_before=settings.news_hard_block_minutes_before,
            hard_block_minutes_after=settings.news_hard_block_minutes_after,
            soft_downgrade_minutes_before=settings.news_soft_downgrade_minutes_before,
            soft_downgrade_minutes_after=settings.news_soft_downgrade_minutes_after,
            soft_downgrade_penalty=Decimal(str(settings.news_soft_downgrade_penalty)),
        ),
        stale_warning_minutes=settings.news_calendar_stale_warning_minutes,
    )

    confluence_service = ConfluenceService(
        market_context_service=market_context_service,
        mtf_service=mtf_service,
        technical_analysis_service=technical_analysis_service,
        smc_service=smc_service,
        price_action_service=price_action_service,
        news_filter=news_filter,
        strategy_engine=strategy_engine,
        event_bus=event_bus,
        config=ConfluenceConfig(
            min_evidence_count=settings.confluence_min_evidence_count,
            primary_timeframe=Timeframe(settings.market_context_primary_timeframe),
        ),
    )

    trade_validation_service = TradeValidationService(
        market_data_service=market_data_service,
        confluence_service=confluence_service,
        mtf_service=mtf_service,
        technical_analysis_service=technical_analysis_service,
        smc_service=smc_service,
        market_context_service=market_context_service,
        news_filter=news_filter,
        strategy_engine=strategy_engine,
        event_bus=event_bus,
        config=TradeValidationConfig(
            primary_timeframe=Timeframe(settings.market_context_primary_timeframe),
        ),
    )

    decision_engine = DecisionEngineService(
        event_bus=event_bus,
        session_factory=session_factory,
        decision_cache=DecisionCache(redis),
    )
    journal_service = JournalService(
        session_factory=session_factory,
        default_user_id=UUID(settings.journal_default_user_id),
    )
    analytics_service = AnalyticsService(session_factory=session_factory)
    risk_management_service = RiskManagementService(
        session_factory=session_factory,
        event_bus=event_bus,
    )
    execution_idempotency = ExecutionIdempotencyCache(redis)
    execution_service = ExecutionService(
        session_factory=session_factory,
        provider=PaperExecutionProvider(
            slippage_pips=Decimal(str(settings.execution_paper_slippage_pips)),
        ),
        idempotency_cache=execution_idempotency,
        event_bus=event_bus,
        execution_mode=settings.execution_mode,
    )
    position_management_service = PositionManagementService(
        session_factory=session_factory,
        market_data_service=market_data_service,
        event_bus=event_bus,
        config=PositionManagementConfig(
            breakeven_at_r=Decimal(str(settings.position_breakeven_at_r)),
            trailing_enabled=settings.position_trailing_enabled,
            trailing_method=settings.position_trailing_method,
            trailing_atr_multiplier=Decimal(str(settings.position_trailing_atr_multiplier)),
            partial_exit_enabled=settings.position_partial_exit_enabled,
            partial_exit_percent=Decimal(str(settings.position_partial_exit_percent)),
            partial_exit_at_r=Decimal(str(settings.position_partial_exit_at_r)),
            tp2_at_r=Decimal(str(settings.position_tp2_at_r)),
            min_lot=Decimal(str(settings.position_min_lot)),
        ),
        primary_timeframe=Timeframe(settings.market_context_primary_timeframe),
        atr_period=settings.market_context_atr_period,
    )
    dedupe_cache = PipelineDedupeCache(
        redis,
        ttl_seconds=settings.pipeline_dedupe_window_seconds,
    )

    pipeline = AnalysisPipelineOrchestrator(
        market_data_service=market_data_service,
        market_context_service=market_context_service,
        mtf_service=mtf_service,
        technical_analysis_service=technical_analysis_service,
        smc_service=smc_service,
        price_action_service=price_action_service,
        news_filter=news_filter,
        confluence_service=confluence_service,
        trade_validation_service=trade_validation_service,
        decision_engine=decision_engine,
        strategy_engine=strategy_engine,
        risk_management_service=risk_management_service,
        dedupe_cache=dedupe_cache,
        event_bus=event_bus,
        session_factory=session_factory,
        config=PipelineConfig(
            primary_timeframe=Timeframe(settings.market_context_primary_timeframe),
            risk_enabled=settings.pipeline_risk_enabled,
            stage_timeout_seconds=settings.pipeline_stage_timeout_seconds,
            dedupe_window_seconds=settings.pipeline_dedupe_window_seconds,
        ),
    )

    market_data_replay = DatabaseMarketDataReplay(session_factory)
    backtest_runner = BacktestRunner(
        pipeline=pipeline,
        market_data_service=market_data_service,
        market_data_replay=market_data_replay,
    )
    ai_explanation_service = AIExplanationService(
        session_factory=session_factory,
        provider=_build_explanation_provider(settings),
        rate_limiter=ExplanationRateLimiter(
            redis,
            limit_per_minute=settings.ai_explanation_rate_limit_per_minute,
        ),
        max_tokens=settings.ai_explanation_max_tokens,
        enabled=settings.ai_explanation_enabled,
    )
    auth_service = AuthService(
        session_factory=session_factory,
        jwt_secret=settings.jwt_secret,
        access_expire_minutes=settings.jwt_access_expire_minutes,
        refresh_expire_days=settings.jwt_refresh_expire_days,
        registration_enabled=settings.auth_registration_enabled,
    )

    return Container(
        settings=settings,
        event_bus=event_bus,
        engine=engine,
        session_factory=session_factory,
        redis=redis,
        pipeline=pipeline,
        market_data_service=market_data_service,
        market_data_replay=market_data_replay,
        mock_provider=MockMarketDataProvider(
            interval_seconds=settings.market_data_mock_interval_seconds,
        ),
        bar_cache=bar_cache,
        strategy_engine=strategy_engine,
        news_filter=news_filter,
        market_context_service=market_context_service,
        mtf_service=mtf_service,
        technical_analysis_service=technical_analysis_service,
        smc_service=smc_service,
        price_action_service=price_action_service,
        confluence_service=confluence_service,
        trade_validation_service=trade_validation_service,
        decision_engine=decision_engine,
        journal_service=journal_service,
        backtest_runner=backtest_runner,
        analytics_service=analytics_service,
        risk_management_service=risk_management_service,
        execution_service=execution_service,
        position_management_service=position_management_service,
        ai_explanation_service=ai_explanation_service,
        auth_service=auth_service,
    )
