"""Dependency injection container."""

from dataclasses import dataclass

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from atlas.application.pipeline.orchestrator import AnalysisPipelineOrchestrator
from atlas.domain.ports.event_bus import EventBusProtocol
from atlas.infrastructure.config import Settings
from atlas.infrastructure.events.in_memory_bus import InMemoryEventBus


@dataclass
class Container:
    """Application service container."""

    settings: Settings
    event_bus: EventBusProtocol
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    redis: Redis
    pipeline: AnalysisPipelineOrchestrator


def build_container(settings: Settings, engine: AsyncEngine, redis: Redis) -> Container:
    """Wire dependencies for the application."""
    from atlas.infrastructure.persistence.database import create_session_factory

    event_bus = InMemoryEventBus()
    session_factory = create_session_factory(engine)
    pipeline = AnalysisPipelineOrchestrator(
        event_bus=event_bus,
        risk_enabled=settings.pipeline_risk_enabled,
    )
    return Container(
        settings=settings,
        event_bus=event_bus,
        engine=engine,
        session_factory=session_factory,
        redis=redis,
        pipeline=pipeline,
    )
