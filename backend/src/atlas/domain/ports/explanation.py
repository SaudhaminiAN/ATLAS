"""AI explanation provider port (Spec 15)."""

from typing import Protocol
from uuid import UUID

from atlas.domain.models.decision import TradingDecision
from atlas.domain.models.explanation import DecisionExplanation


class IExplanationProvider(Protocol):
    """Generate natural-language text from a prompt."""

    async def generate(self, prompt: str, max_tokens: int) -> str:
        """Return explanation text."""
        ...


class AIExplanationServiceProtocol(Protocol):
    """Explain finalized decisions (read-only)."""

    def build_prompt(self, decision: TradingDecision) -> str:
        """Build LLM prompt from decision snapshot only."""
        ...

    async def explain(self, decision_id: UUID) -> DecisionExplanation | None:
        """Generate or return cached explanation for a decision."""
        ...
