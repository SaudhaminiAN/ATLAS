"""Journal entry persistence (Spec 13)."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from atlas.domain.models.journal import JournalEntry
from atlas.infrastructure.persistence.models import JournalEntryModel


def entry_to_domain(model: JournalEntryModel) -> JournalEntry:
    tags = tuple(model.tags) if model.tags else ()
    return JournalEntry(
        id=model.id,
        decision_id=model.decision_id,
        trade_id=model.trade_id,
        user_id=model.user_id,
        entry_type=model.entry_type,
        content=model.content,
        tags=tags,
        created_at=model.created_at,
    )


class JournalRepository:
    """Trader notes persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_note(
        self,
        *,
        trade_id: UUID,
        user_id: UUID,
        content: str,
        tags: list[str],
        decision_id: UUID | None = None,
    ) -> JournalEntry:
        entry = JournalEntry(
            id=uuid4(),
            decision_id=decision_id,
            trade_id=trade_id,
            user_id=user_id,
            entry_type="note",
            content=content,
            tags=tuple(tags),
            created_at=datetime.now(UTC),
        )
        model = JournalEntryModel(
            id=entry.id,
            decision_id=entry.decision_id,
            trade_id=entry.trade_id,
            user_id=entry.user_id,
            entry_type=entry.entry_type,
            content=entry.content,
            tags=list(entry.tags),
            created_at=entry.created_at,
        )
        self._session.add(model)
        await self._session.commit()
        return entry

    async def list_by_trade(self, trade_id: UUID) -> list[JournalEntry]:
        result = await self._session.execute(
            select(JournalEntryModel)
            .where(JournalEntryModel.trade_id == trade_id)
            .order_by(JournalEntryModel.created_at.asc())
        )
        return [entry_to_domain(row) for row in result.scalars().all()]
