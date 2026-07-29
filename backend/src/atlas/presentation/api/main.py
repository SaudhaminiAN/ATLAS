"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from atlas.application.container import build_container
from atlas.infrastructure.cache.redis_client import create_redis
from atlas.infrastructure.config import Settings, get_settings
from atlas.infrastructure.logging import configure_logging
from atlas.infrastructure.persistence.database import create_engine
from atlas.presentation.api.routers import health

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

    logger.info("atlas_started", api_prefix=settings.api_prefix)
    yield

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

    return app


app = create_app()
