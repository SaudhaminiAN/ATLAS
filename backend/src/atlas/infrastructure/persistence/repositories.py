"""Instrument and OHLCV persistence."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from atlas.domain.models.decision import TradingDecision
from atlas.domain.models.enums import Direction, Timeframe
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.journal import DecisionFilters
from atlas.domain.models.news import EconomicEvent, EventImpact
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.pipeline import PipelineRun, StageResult
from atlas.domain.models.strategy import DEFAULT_PROFILE_ID, StrategyProfile
from atlas.infrastructure.persistence.decision_serializers import (
    confluence_from_dict,
    confluence_to_dict,
    news_status_from_dict,
    news_status_to_dict,
    validation_from_dict,
    validation_to_dict,
)
from atlas.infrastructure.persistence.models import (
    DecisionModel,
    EconomicEventModel,
    InstrumentModel,
    OHLCVBarModel,
    PipelineRunModel,
    RiskProfileModel,
    StrategyProfileModel,
)


def instrument_to_domain(model: InstrumentModel) -> Instrument:
    """Map ORM instrument to domain."""
    return Instrument(
        id=model.id,
        symbol=model.symbol,
        display_name=model.display_name,
        pip_size=Decimal(str(model.pip_size)),
        lot_size=Decimal(str(model.lot_size)),
        is_active=model.is_active,
    )


def bar_to_domain(model: OHLCVBarModel, instrument: Instrument) -> OHLCVBar:
    """Map ORM bar to domain."""
    return OHLCVBar(
        instrument=instrument,
        timeframe=Timeframe(model.timeframe),
        open_time=model.open_time,
        open=Decimal(str(model.open)),
        high=Decimal(str(model.high)),
        low=Decimal(str(model.low)),
        close=Decimal(str(model.close)),
        volume=Decimal(str(model.volume)),
        is_outlier=model.is_outlier,
        quality_flags=list(model.quality_flags or []),
    )


class InstrumentRepository:
    """Instrument lookup."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_symbol(self, symbol: str) -> Instrument | None:
        """Find instrument by symbol."""
        result = await self._session.execute(
            select(InstrumentModel).where(InstrumentModel.symbol == symbol.upper())
        )
        row = result.scalar_one_or_none()
        return instrument_to_domain(row) if row else None

    async def list_active(self) -> list[Instrument]:
        """List active instruments."""
        result = await self._session.execute(
            select(InstrumentModel).where(InstrumentModel.is_active.is_(True))
        )
        return [instrument_to_domain(r) for r in result.scalars().all()]


class OHLCVBarRepository:
    """OHLCV bar persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(self, bar: OHLCVBar) -> bool:
        """Insert bar; return False if duplicate."""
        stmt = (
            insert(OHLCVBarModel)
            .values(
                instrument_id=bar.instrument.id,
                timeframe=bar.timeframe.value,
                open_time=bar.open_time,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
                is_outlier=bar.is_outlier,
                quality_flags=bar.quality_flags,
            )
            .on_conflict_do_nothing(
                index_elements=["instrument_id", "timeframe", "open_time"],
            )
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount > 0

    async def count(self, instrument_id: UUID, timeframe: Timeframe) -> int:
        """Count bars for instrument/timeframe."""
        result = await self._session.execute(
            select(func.count())
            .select_from(OHLCVBarModel)
            .where(
                OHLCVBarModel.instrument_id == instrument_id,
                OHLCVBarModel.timeframe == timeframe.value,
            )
        )
        return int(result.scalar_one())

    async def delete_for_instrument(self, instrument_id: UUID, timeframe: Timeframe) -> int:
        """Remove all bars for instrument/timeframe (mock bootstrap only)."""
        result = await self._session.execute(
            delete(OHLCVBarModel).where(
                OHLCVBarModel.instrument_id == instrument_id,
                OHLCVBarModel.timeframe == timeframe.value,
            )
        )
        await self._session.commit()
        return result.rowcount or 0

    async def exists(
        self, instrument_id: UUID, timeframe: Timeframe, open_time: datetime
    ) -> bool:
        """Check if bar already exists."""
        result = await self._session.execute(
            select(OHLCVBarModel.id).where(
                OHLCVBarModel.instrument_id == instrument_id,
                OHLCVBarModel.timeframe == timeframe.value,
                OHLCVBarModel.open_time == open_time,
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_latest(self, instrument_id: UUID, timeframe: Timeframe) -> OHLCVBarModel | None:
        """Get most recent bar."""
        result = await self._session.execute(
            select(OHLCVBarModel)
            .where(
                OHLCVBarModel.instrument_id == instrument_id,
                OHLCVBarModel.timeframe == timeframe.value,
            )
            .order_by(OHLCVBarModel.open_time.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_history(
        self,
        instrument_id: UUID,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
        limit: int = 500,
    ) -> list[OHLCVBarModel]:
        """Fetch bars in time range."""
        result = await self._session.execute(
            select(OHLCVBarModel)
            .where(
                OHLCVBarModel.instrument_id == instrument_id,
                OHLCVBarModel.timeframe == timeframe.value,
                OHLCVBarModel.open_time >= start,
                OHLCVBarModel.open_time <= end,
            )
            .order_by(OHLCVBarModel.open_time.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_bars_before(
        self,
        instrument_id: UUID,
        timeframe: Timeframe,
        before: datetime,
        limit: int,
    ) -> list[OHLCVBarModel]:
        """Fetch bars strictly before a timestamp (for ATR lookback)."""
        result = await self._session.execute(
            select(OHLCVBarModel)
            .where(
                OHLCVBarModel.instrument_id == instrument_id,
                OHLCVBarModel.timeframe == timeframe.value,
                OHLCVBarModel.open_time < before,
            )
            .order_by(OHLCVBarModel.open_time.desc())
            .limit(limit)
        )
        rows = list(result.scalars().all())
        rows.reverse()
        return rows

    async def get_bars_up_to(
        self,
        instrument_id: UUID,
        timeframe: Timeframe,
        as_of: datetime,
        limit: int,
    ) -> list[OHLCVBarModel]:
        """Fetch bars with open_time <= as_of (no look-ahead)."""
        result = await self._session.execute(
            select(OHLCVBarModel)
            .where(
                OHLCVBarModel.instrument_id == instrument_id,
                OHLCVBarModel.timeframe == timeframe.value,
                OHLCVBarModel.open_time <= as_of,
            )
            .order_by(OHLCVBarModel.open_time.desc())
            .limit(limit)
        )
        rows = list(result.scalars().all())
        rows.reverse()
        return rows


def strategy_profile_to_domain(model: StrategyProfileModel) -> StrategyProfile:
    """Map ORM strategy profile to domain."""
    from atlas.domain.models.enums import Direction, TradingSession

    config = model.config
    return StrategyProfile(
        id=model.id,
        name=model.name,
        min_confluence_score=Decimal(str(config["min_confluence_score"])),
        enabled_directions=tuple(Direction(d) for d in config["enabled_directions"]),
        confluence_weights={
            k: Decimal(str(v)) for k, v in config["confluence_weights"].items()
        },
        active_timeframes=tuple(Timeframe(tf) for tf in config["active_timeframes"]),
        allowed_sessions=tuple(TradingSession(s) for s in config["allowed_sessions"]),
        validation_rule_flags=dict(config["validation_rules"]),
        is_active=model.is_active,
        updated_at=model.updated_at,
    )


class StrategyProfileRepository:
    """Strategy profile persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[StrategyProfileModel]:
        """Return all profiles ordered by id."""
        result = await self._session.execute(
            select(StrategyProfileModel).order_by(StrategyProfileModel.id)
        )
        return list(result.scalars().all())

    async def get_by_id(self, profile_id: str) -> StrategyProfileModel | None:
        """Find profile by id."""
        result = await self._session.execute(
            select(StrategyProfileModel).where(StrategyProfileModel.id == profile_id)
        )
        return result.scalar_one_or_none()

    async def get_active(self) -> StrategyProfileModel | None:
        """Return the active profile if one exists."""
        result = await self._session.execute(
            select(StrategyProfileModel).where(StrategyProfileModel.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def set_active(self, profile_id: str) -> StrategyProfileModel | None:
        """Deactivate all profiles and activate the target; return activated row."""
        target = await self.get_by_id(profile_id)
        if not target:
            return None

        result = await self._session.execute(select(StrategyProfileModel))
        for row in result.scalars().all():
            row.is_active = row.id == profile_id
        await self._session.commit()
        await self._session.refresh(target)
        return target

    async def ensure_default_active(self) -> StrategyProfileModel:
        """Ensure default profile is active when none is set."""
        active = await self.get_active()
        if active:
            return active

        default = await self.get_by_id(DEFAULT_PROFILE_ID)
        if not default:
            raise RuntimeError(f"Default strategy profile '{DEFAULT_PROFILE_ID}' not found")

        return await self.set_active(DEFAULT_PROFILE_ID) or default


def economic_event_to_domain(model: EconomicEventModel) -> EconomicEvent:
    """Map ORM economic event to domain."""
    return EconomicEvent(
        id=model.id,
        name=model.name,
        currency=model.currency,
        impact=EventImpact(model.impact),
        scheduled_at=model.scheduled_at,
        source=model.source,
        actual=Decimal(str(model.actual)) if model.actual is not None else None,
        forecast=Decimal(str(model.forecast)) if model.forecast is not None else None,
        previous=Decimal(str(model.previous)) if model.previous is not None else None,
    )


class EconomicEventRepository:
    """Economic calendar persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_many(self, events: list[EconomicEvent]) -> None:
        """Insert or update events by primary key."""
        for event in events:
            stmt = (
                insert(EconomicEventModel)
                .values(
                    id=event.id,
                    name=event.name,
                    currency=event.currency,
                    impact=event.impact.value,
                    scheduled_at=event.scheduled_at,
                    actual=event.actual,
                    forecast=event.forecast,
                    previous=event.previous,
                    source=event.source,
                )
                .on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "name": event.name,
                        "currency": event.currency,
                        "impact": event.impact.value,
                        "scheduled_at": event.scheduled_at,
                        "actual": event.actual,
                        "forecast": event.forecast,
                        "previous": event.previous,
                        "source": event.source,
                    },
                )
            )
            await self._session.execute(stmt)
        await self._session.commit()

    async def list_between(
        self,
        start: datetime,
        end: datetime,
        *,
        impact: EventImpact | None = None,
    ) -> list[EconomicEvent]:
        """Fetch events in a time range."""
        query = select(EconomicEventModel).where(
            EconomicEventModel.scheduled_at >= start,
            EconomicEventModel.scheduled_at <= end,
        )
        if impact is not None:
            query = query.where(EconomicEventModel.impact == impact.value)
        query = query.order_by(EconomicEventModel.scheduled_at.asc())
        result = await self._session.execute(query)
        return [economic_event_to_domain(row) for row in result.scalars().all()]


def _stage_results_to_json(stage_results: dict[str, StageResult]) -> dict:
    return {
        name: {
            "stage_name": result.stage_name,
            "status": result.status,
            "duration_ms": result.duration_ms,
            "error": result.error,
        }
        for name, result in stage_results.items()
    }


class PipelineRunRepository:
    """Pipeline run audit persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(self, run: PipelineRun) -> None:
        """Persist a completed or failed pipeline run."""
        if run.instrument is None or run.trigger_bar_time is None:
            return

        model = PipelineRunModel(
            id=run.id,
            correlation_id=run.correlation_id,
            instrument_id=run.instrument.id,
            trigger_timeframe=run.trigger_timeframe.value,
            trigger_bar_time=run.trigger_bar_time,
            status=run.status.value,
            stage_results=_stage_results_to_json(run.stage_results),
            duration_ms=run.duration_ms,
            created_at=run.started_at,
        )
        self._session.add(model)
        await self._session.commit()


def _decision_model_to_domain(model: DecisionModel, instrument: Instrument) -> TradingDecision:
    confluence = (
        confluence_from_dict(model.confluence_snapshot, instrument)
        if model.confluence_snapshot
        else None
    )
    validation = (
        validation_from_dict(model.validation_result, instrument)
        if model.validation_result
        else None
    )
    news = news_status_from_dict(model.news_status) if model.news_status else None
    return TradingDecision(
        id=model.id,
        instrument=instrument,
        direction=Direction(model.direction),
        is_actionable=model.is_actionable,
        confluence_score=Decimal(str(model.confidence)),
        strategy_id=model.strategy_profile_id,
        reason=model.reason,
        correlation_id=model.correlation_id,
        decided_at=model.created_at,
        confluence_snapshot=confluence,
        validation_snapshot=validation,
        risk_snapshot=model.risk_snapshot,
        news_status=news,
    )


class DecisionRepository:
    """Trading decision persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _decision_values(self, decision: TradingDecision) -> dict:
        return {
            "id": decision.id,
            "instrument_id": decision.instrument.id,
            "correlation_id": decision.correlation_id,
            "direction": decision.direction.value,
            "is_actionable": decision.is_actionable,
            "reason": decision.reason,
            "confidence": decision.confluence_score,
            "strategy_profile_id": decision.strategy_id,
            "confluence_snapshot": (
                confluence_to_dict(decision.confluence_snapshot)
                if decision.confluence_snapshot
                else None
            ),
            "validation_result": (
                validation_to_dict(decision.validation_snapshot)
                if decision.validation_snapshot
                else None
            ),
            "risk_snapshot": decision.risk_snapshot,
            "news_status": (
                news_status_to_dict(decision.news_status) if decision.news_status else None
            ),
            "created_at": decision.decided_at,
        }

    async def insert(self, decision: TradingDecision) -> None:
        """Persist an immutable decision record."""
        model = DecisionModel(**self._decision_values(decision))
        self._session.add(model)
        await self._session.commit()

    async def insert_idempotent(self, decision: TradingDecision) -> bool:
        """Insert decision; return True if a new row was created."""
        stmt = (
            insert(DecisionModel)
            .values(**self._decision_values(decision))
            .on_conflict_do_nothing(index_elements=["id"])
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount > 0

    def _apply_filters(self, query, filters: DecisionFilters):
        if filters.symbol:
            query = query.where(InstrumentModel.symbol == filters.symbol.upper())
        if filters.direction is not None:
            query = query.where(DecisionModel.direction == filters.direction.value)
        if filters.is_actionable is not None:
            query = query.where(DecisionModel.is_actionable.is_(filters.is_actionable))
        if filters.correlation_id:
            query = query.where(DecisionModel.correlation_id == filters.correlation_id)
        if filters.start is not None:
            query = query.where(DecisionModel.created_at >= filters.start)
        if filters.end is not None:
            query = query.where(DecisionModel.created_at <= filters.end)
        return query

    async def query(self, filters: DecisionFilters) -> list[TradingDecision]:
        """Return filtered paginated decisions."""
        query = (
            select(DecisionModel, InstrumentModel)
            .join(InstrumentModel, DecisionModel.instrument_id == InstrumentModel.id)
            .order_by(DecisionModel.created_at.desc())
            .limit(filters.limit)
            .offset(filters.offset)
        )
        query = self._apply_filters(query, filters)
        result = await self._session.execute(query)
        return [
            _decision_model_to_domain(decision_model, instrument_to_domain(instrument_model))
            for decision_model, instrument_model in result.all()
        ]

    async def count(self, filters: DecisionFilters) -> int:
        """Count decisions matching filters."""
        query = select(func.count()).select_from(DecisionModel).join(
            InstrumentModel, DecisionModel.instrument_id == InstrumentModel.id
        )
        query = self._apply_filters(query, filters)
        result = await self._session.execute(query)
        return int(result.scalar_one())

    async def get_latest(self, symbol: str) -> TradingDecision | None:
        """Return the most recent decision for a symbol."""
        result = await self._session.execute(
            select(DecisionModel, InstrumentModel)
            .join(InstrumentModel, DecisionModel.instrument_id == InstrumentModel.id)
            .where(InstrumentModel.symbol == symbol.upper())
            .order_by(DecisionModel.created_at.desc())
            .limit(1)
        )
        row = result.first()
        if not row:
            return None
        decision_model, instrument_model = row
        return _decision_model_to_domain(decision_model, instrument_to_domain(instrument_model))

    async def get_by_id(self, decision_id: UUID) -> TradingDecision | None:
        """Return a decision by primary key."""
        result = await self._session.execute(
            select(DecisionModel, InstrumentModel)
            .join(InstrumentModel, DecisionModel.instrument_id == InstrumentModel.id)
            .where(DecisionModel.id == decision_id)
        )
        row = result.first()
        if not row:
            return None
        decision_model, instrument_model = row
        return _decision_model_to_domain(decision_model, instrument_to_domain(instrument_model))

    async def list_history(
        self,
        symbol: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TradingDecision]:
        """Return paginated decision history for a symbol."""
        result = await self._session.execute(
            select(DecisionModel, InstrumentModel)
            .join(InstrumentModel, DecisionModel.instrument_id == InstrumentModel.id)
            .where(InstrumentModel.symbol == symbol.upper())
            .order_by(DecisionModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [
            _decision_model_to_domain(decision_model, instrument_to_domain(instrument_model))
            for decision_model, instrument_model in result.all()
        ]


class RiskProfileRepository:
    """Risk profile persistence (Spec 10)."""

    DEFAULT_ID = "default"

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, profile_id: str = DEFAULT_ID):
        from atlas.infrastructure.persistence.risk_serializers import risk_profile_from_dict

        result = await self._session.execute(
            select(RiskProfileModel).where(RiskProfileModel.id == profile_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        data = dict(row.config)
        data["id"] = row.id
        data["updated_at"] = row.updated_at
        return risk_profile_from_dict(data)

    async def update(self, profile):
        from datetime import UTC, datetime

        from atlas.infrastructure.persistence.risk_serializers import (
            risk_profile_from_dict,
            risk_profile_to_dict,
        )

        values = risk_profile_to_dict(profile)
        profile_id = values.pop("id")
        result = await self._session.execute(
            select(RiskProfileModel).where(RiskProfileModel.id == profile_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise ValueError(f"Risk profile not found: {profile_id}")
        row.config = values
        row.updated_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(row)
        data = dict(row.config)
        data["id"] = row.id
        data["updated_at"] = row.updated_at
        return risk_profile_from_dict(data)
