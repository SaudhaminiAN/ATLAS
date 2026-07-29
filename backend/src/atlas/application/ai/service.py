"""AI explanation application service (Spec 15)."""

from dataclasses import dataclass
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from atlas.domain.models.decision import TradingDecision
from atlas.domain.models.explanation import DecisionExplanation
from atlas.domain.ports.explanation import IExplanationProvider
from atlas.domain.services.explanation_prompt import build_prompt
from atlas.infrastructure.cache.explanation_rate_limit import ExplanationRateLimiter
from atlas.infrastructure.persistence.explanation_repository import ExplanationRepository
from atlas.infrastructure.persistence.repositories import DecisionRepository

logger = structlog.get_logger(__name__)


class ExplanationRateLimitError(Exception):
    """Raised when explanation rate limit is exceeded."""


class DecisionNotFoundError(Exception):
    """Raised when decision does not exist."""


@dataclass
class AIExplanationService:
    """Generate and cache natural-language decision explanations."""

    session_factory: async_sessionmaker[AsyncSession]
    provider: IExplanationProvider
    rate_limiter: ExplanationRateLimiter
    max_tokens: int = 500
    enabled: bool = True

    def build_prompt(self, decision: TradingDecision) -> str:
        return build_prompt(decision)

    async def explain(self, decision_id: UUID) -> DecisionExplanation | None:
        """Return cached explanation or generate a new one."""
        if not self.enabled:
            return None

        async with self.session_factory() as session:
            existing = await ExplanationRepository(session).get_by_decision_id(decision_id)
            if existing is not None:
                return existing

            decision = await DecisionRepository(session).get_by_id(decision_id)
            if decision is None:
                raise DecisionNotFoundError(str(decision_id))

        if not await self.rate_limiter.allow():
            raise ExplanationRateLimitError("Explanation rate limit exceeded")

        prompt = self.build_prompt(decision)
        provider_name = getattr(self.provider, "name", "unknown")

        try:
            content = await self.provider.generate(prompt, self.max_tokens)
        except Exception:
            logger.exception("explanation_generation_failed", decision_id=str(decision_id))
            return None

        async with self.session_factory() as session:
            stored = await ExplanationRepository(session).create(
                decision_id=decision_id,
                content=content,
                provider=provider_name,
            )
            logger.info(
                "explanation_generated",
                decision_id=str(decision_id),
                provider=provider_name,
            )
            return stored

    async def get_explanation(self, decision_id: UUID) -> DecisionExplanation | None:
        async with self.session_factory() as session:
            return await ExplanationRepository(session).get_by_decision_id(decision_id)
