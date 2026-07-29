"""Strategy profile domain model."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from atlas.domain.models.enums import Direction, Timeframe, TradingSession

DEFAULT_PROFILE_ID = "xauusd_conservative"

KNOWN_VALIDATION_RULES = frozenset(
    {
        "mtf_alignment_minimum",
        "confluence_score_minimum",
        "no_counter_trend",
        "minimum_rr_potential",
        "news_block",
        "session_check",
        "spread_check",
        "volatility_check",
    }
)


@dataclass(frozen=True, slots=True)
class StrategyProfile:
    """Configurable strategy profile for analysis modules."""

    id: str
    name: str
    min_confluence_score: Decimal
    enabled_directions: tuple[Direction, ...]
    confluence_weights: dict[str, Decimal]
    active_timeframes: tuple[Timeframe, ...]
    allowed_sessions: tuple[TradingSession, ...]
    validation_rule_flags: dict[str, bool]
    is_active: bool
    updated_at: datetime

    def is_direction_enabled(self, direction: Direction) -> bool:
        """Return True if the profile allows trading in this direction."""
        if direction == Direction.WAIT:
            return True
        return direction in self.enabled_directions

    def is_rule_enabled(self, rule_name: str) -> bool:
        """Return True if a validation rule is enabled for this profile."""
        return self.validation_rule_flags.get(rule_name, False)
