"""FastAPI application factory."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from atlas.application.ai.handler import make_ai_explanation_handler
from atlas.application.container import build_container
from atlas.application.execution.handler import make_execution_decision_handler
from atlas.application.journal.handler import make_journal_decision_handler
from atlas.application.journal.trade_handler import make_journal_trade_handler
from atlas.application.market_context.handler import make_bar_context_handler
from atlas.application.position_management.handler import make_position_management_bar_handler
from atlas.application.market_data.stream import run_mock_market_data_stream
from atlas.application.news.sync import run_news_calendar_sync
from atlas.application.pipeline.handler import make_pipeline_bar_handler
from atlas.infrastructure.cache.redis_client import create_redis
from atlas.infrastructure.config import Settings, get_settings
from atlas.infrastructure.logging import configure_logging
from atlas.infrastructure.persistence.database import create_engine
from atlas.presentation.api.routers import (
    analysis,
    analytics,
    backtest,
    decisions,
    explanations,
    health,
    instruments,
    journal,
    market_data,
    news,
    risk,
    strategy,
    trades,
)
from atlas.presentation.api.websocket import routes as ws_routes
from atlas.presentation.api.websocket.manager import WebSocketManager

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup and shutdown lifecycle."""
    settings: Settings = app.state.settings
    configure_logging(settings)
    logger.info("atlas_starting", environment=settings.environment)

    engine = create_engine(settings)
    redis = await create_redis(settings.redis_url)
    container = build_container(settings, engine, redis)
    app.state.container = container

    ws_manager = WebSocketManager()
    app.state.ws_manager = ws_manager
    container.event_bus.subscribe("market_data.bar.received", ws_manager.on_bar_received)
    container.event_bus.subscribe("trade.sl_moved", ws_manager.on_trade_event)
    container.event_bus.subscribe("trade.partial_closed", ws_manager.on_trade_event)
    container.event_bus.subscribe("trade.closed", ws_manager.on_trade_event)
    container.event_bus.subscribe("decision.emitted", ws_manager.on_decision_emitted)
    container.event_bus.subscribe(
        "decision.emitted",
        make_journal_decision_handler(container),
    )
    container.event_bus.subscribe(
        "decision.emitted",
        make_ai_explanation_handler(container, settings),
    )
    for trade_event in (
        "trade.opened",
        "trade.rejected",
        "trade.sl_moved",
        "trade.partial_closed",
        "trade.closed",
    ):
        container.event_bus.subscribe(trade_event, make_journal_trade_handler(container))
    if settings.execution_enabled:
        container.event_bus.subscribe(
            "decision.emitted",
            make_execution_decision_handler(container),
        )
    container.event_bus.subscribe(
        "market_data.bar.received",
        make_bar_context_handler(container, settings),
    )
    container.event_bus.subscribe(
        "market_data.bar.received",
        make_pipeline_bar_handler(container, settings),
    )
    container.event_bus.subscribe(
        "market_data.bar.received",
        make_position_management_bar_handler(container, settings),
    )

    mock_task: asyncio.Task | None = None
    news_task: asyncio.Task | None = None
    if settings.market_data_mock_enabled:
        mock_task = asyncio.create_task(run_mock_market_data_stream(container, settings))
    if settings.news_mock_enabled:
        news_task = asyncio.create_task(run_news_calendar_sync(container, settings))

    logger.info("atlas_started", api_prefix=settings.api_prefix)
    yield

    if mock_task:
        mock_task.cancel()
        try:
            await mock_task
        except asyncio.CancelledError:
            pass

    if news_task:
        news_task.cancel()
        try:
            await news_task
        except asyncio.CancelledError:
            pass

    await redis.aclose()
    await engine.dispose()
    logger.info("atlas_stopped")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = settings or get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url=f"{settings.api_prefix}/docs",
        openapi_url=f"{settings.api_prefix}/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix=settings.api_prefix)
    app.include_router(instruments.router, prefix=settings.api_prefix)
    app.include_router(market_data.router, prefix=settings.api_prefix)
    app.include_router(strategy.router, prefix=settings.api_prefix)
    app.include_router(news.router, prefix=settings.api_prefix)
    app.include_router(analysis.router, prefix=settings.api_prefix)
    app.include_router(decisions.router, prefix=settings.api_prefix)
    app.include_router(explanations.router, prefix=settings.api_prefix)
    app.include_router(journal.router, prefix=settings.api_prefix)
    app.include_router(backtest.router, prefix=settings.api_prefix)
    app.include_router(analytics.router, prefix=settings.api_prefix)
    app.include_router(risk.router, prefix=settings.api_prefix)
    app.include_router(trades.router, prefix=settings.api_prefix)
    app.include_router(ws_routes.router, prefix=settings.api_prefix)

    return app


app = create_app()
