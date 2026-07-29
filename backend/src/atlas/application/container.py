"""Dependency injection container."""

from dataclasses import dataclass
from decimal import Decimal

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from atlas.application.market_context.service import MarketContextConfig, MarketContextService
from atlas.application.market_data.service import MarketDataConfig, MarketDataService
from atlas.application.news.service import NewsFilterService
from atlas.application.pipeline.orchestrator import AnalysisPipelineOrchestrator
from atlas.application.strategy.service import StrategyEngineService
from atlas.domain.models.enums import Timeframe
from atlas.domain.ports.event_bus import EventBusProtocol
from atlas.domain.services.news_window import NewsFilterConfig
from atlas.infrastructure.cache.bar_cache import BarCache
from atlas.infrastructure.cache.context_cache import ContextCache
from atlas.infrastructure.cache.news_cache import NewsEventCache
from atlas.infrastructure.cache.strategy_cache import StrategyProfileCache
from atlas.infrastructure.config import Settings
from atlas.infrastructure.events.in_memory_bus import InMemoryEventBus
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


def build_container(settings: Settings, engine: AsyncEngine, redis: Redis) -> Container:
    """Wire dependencies for the application."""
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

    return Container(
        settings=settings,
        event_bus=event_bus,
        engine=engine,
        session_factory=session_factory,
        redis=redis,
        pipeline=AnalysisPipelineOrchestrator(
            event_bus=event_bus,
            risk_enabled=settings.pipeline_risk_enabled,
        ),
        market_data_service=market_data_service,
        market_data_replay=DatabaseMarketDataReplay(session_factory),
        mock_provider=MockMarketDataProvider(
            interval_seconds=settings.market_data_mock_interval_seconds,
        ),
        bar_cache=bar_cache,
        strategy_engine=StrategyEngineService(
            session_factory=session_factory,
            event_bus=event_bus,
            profile_cache=profile_cache,
        ),
        news_filter=NewsFilterService(
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
        ),
        market_context_service=market_context_service,
    )
