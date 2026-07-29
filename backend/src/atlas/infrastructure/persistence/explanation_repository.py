"""Decision explanation persistence (Spec 15)."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from atlas.domain.models.explanation import DecisionExplanation
from atlas.infrastructure.persistence.models import DecisionExplanationModel


def explanation_to_domain(model: DecisionExplanationModel) -> DecisionExplanation:
    return DecisionExplanation(
        id=model.id,
        decision_id=model.decision_id,
        content=model.content,
        provider=model.provider,
        created_at=model.created_at,
    )


class ExplanationRepository:
    """Persist and retrieve decision explanations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_decision_id(self, decision_id: UUID) -> DecisionExplanation | None:
        result = await self._session.execute(
            select(DecisionExplanationModel).where(
                DecisionExplanationModel.decision_id == decision_id
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return explanation_to_domain(row)

    async def insert(self, explanation: DecisionExplanation) -> DecisionExplanation:
        """Insert explanation; on conflict return existing row."""
        existing = await self.get_by_decision_id(explanation.decision_id)
        if existing is not None:
            return existing

        stmt = (
            insert(DecisionExplanationModel)
            .values(
                id=explanation.id,
                decision_id=explanation.decision_id,
                content=explanation.content,
                provider=explanation.provider,
                created_at=explanation.created_at,
            )
            .on_conflict_do_nothing(index_elements=["decision_id"])
        )
        await self._session.execute(stmt)
        await self._session.commit()

        stored = await self.get_by_decision_id(explanation.decision_id)
        return stored if stored is not None else explanation

    async def create(
        self,
        *,
        decision_id: UUID,
        content: str,
        provider: str,
    ) -> DecisionExplanation:
        explanation = DecisionExplanation(
            id=uuid4(),
            decision_id=decision_id,
            content=content,
            provider=provider,
            created_at=datetime.now(UTC),
        )
        return await self.insert(explanation)
