"""Risk management application service (Spec 10)."""

from dataclasses import dataclass, field
from decimal import Decimal

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from atlas.domain.events.base import DomainEvent
from atlas.domain.models.enums import Direction
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.risk import RiskCheckResult, RiskProfile
from atlas.domain.models.smc import SMCAnalysisResult
from atlas.domain.models.technical import TechnicalAnalysisResult
from atlas.domain.ports.event_bus import EventBusProtocol
from atlas.domain.services.risk_management import calculate_risk
from atlas.infrastructure.persistence.repositories import RiskProfileRepository
from atlas.infrastructure.persistence.risk_serializers import risk_result_to_dict

logger = structlog.get_logger(__name__)


@dataclass
class RiskManagementService:
    """Calculate SL/TP, position size, and enforce account limits."""

    session_factory: async_sessionmaker[AsyncSession]
    event_bus: EventBusProtocol
    open_positions_count: int = 0
    daily_pnl: Decimal = field(default_factory=lambda: Decimal("0"))

    async def get_profile(self, profile_id: str = "default") -> RiskProfile:
        async with self.session_factory() as session:
            profile = await RiskProfileRepository(session).get(profile_id)
        if profile is None:
            raise ValueError(f"Risk profile not found: {profile_id}")
        return profile

    async def update_profile(self, profile: RiskProfile) -> RiskProfile:
        async with self.session_factory() as session:
            return await RiskProfileRepository(session).update(profile)

    def calculate(
        self,
        direction: Direction,
        entry_price: Decimal,
        technical: TechnicalAnalysisResult,
        smc: SMCAnalysisResult,
        atr: Decimal,
        instrument: Instrument,
        profile: RiskProfile,
    ) -> RiskCheckResult:
        """Run risk formulas and publish events."""
        result = calculate_risk(
            direction,
            entry_price,
            technical,
            smc,
            atr,
            instrument,
            profile,
            open_positions_count=self.open_positions_count,
            daily_pnl=self.daily_pnl,
        )
        payload = risk_result_to_dict(result)
        if result.within_limits:
            self.event_bus.publish(
                DomainEvent(
                    event_type="risk.calculated",
                    correlation_id=f"risk-{instrument.symbol}-{entry_price}",
                    payload=payload,
                )
            )
            logger.info("risk_calculated", symbol=instrument.symbol, entry=str(entry_price))
        else:
            self.event_bus.publish(
                DomainEvent(
                    event_type="risk.limit.breached",
                    correlation_id=f"risk-{instrument.symbol}-{entry_price}",
                    payload=payload,
                )
            )
            logger.warning(
                "risk_limit_breached",
                symbol=instrument.symbol,
                reason=result.breach_reason,
            )
        return result
