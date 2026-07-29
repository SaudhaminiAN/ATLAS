"""ORM models."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from atlas.infrastructure.persistence.base import Base


class InstrumentModel(Base):
    """Instrument table."""

    __tablename__ = "instruments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    pip_size: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)
    lot_size: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class StrategyProfileModel(Base):
    """Strategy profile configuration."""

    __tablename__ = "strategy_profiles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class OHLCVBarModel(Base):
    """OHLCV bar storage."""

    __tablename__ = "ohlcv_bars"
    __table_args__ = (
        UniqueConstraint("instrument_id", "timeframe", "open_time", name="uq_ohlcv_bar"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("instruments.id"), nullable=False
    )
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    high: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    low: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    close: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    volume: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    is_outlier: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    quality_flags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class MigrationMarkerModel(Base):
    """Tracks schema bootstrap for health checks."""

    __tablename__ = "schema_metadata"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)


class EconomicEventModel(Base):
    """Synced economic calendar events."""

    __tablename__ = "economic_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    impact: Mapped[str] = mapped_column(String(16), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actual: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    forecast: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    previous: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class PipelineRunModel(Base):
    """Pipeline execution audit log."""

    __tablename__ = "pipeline_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("instruments.id"), nullable=False
    )
    trigger_timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    trigger_bar_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    stage_results: Mapped[dict] = mapped_column(JSONB, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class RiskProfileModel(Base):
    """Account risk profile configuration."""

    __tablename__ = "risk_profiles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class TradeModel(Base):
    """Executed or rejected trade record."""

    __tablename__ = "trades"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    decision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False)
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("instruments.id"), nullable=False
    )
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    entry_price: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    fill_price: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    stop_loss: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    take_profit: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    position_size: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    execution_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    realized_pnl: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    initial_stop_loss: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    remaining_size: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    partial_realized_pnl: Mapped[float] = mapped_column(
        Numeric(18, 6), nullable=False, server_default="0"
    )
    breakeven_applied: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    partial_exit_applied: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TradeEventModel(Base):
    """Append-only trade lifecycle audit."""

    __tablename__ = "trade_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    trade_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trades.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class JournalEntryModel(Base):
    """Trader notes attached to decisions or trades (Spec 13)."""

    __tablename__ = "journal_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    decision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    trade_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trades.id"), nullable=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    entry_type: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class DecisionModel(Base):
    """Immutable trading decision record."""

    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("instruments.id"), nullable=False
    )
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    is_actionable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str] = mapped_column(String(512), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    strategy_profile_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("strategy_profiles.id"), nullable=False
    )
    confluence_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    validation_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    risk_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    news_status: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class DecisionExplanationModel(Base):
    """Natural-language explanation for a decision (Spec 15)."""

    __tablename__ = "decision_explanations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decisions.id"), unique=True, nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
