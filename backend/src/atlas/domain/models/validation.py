"""Trade validation domain models."""

from dataclasses import dataclass
from datetime import datetime

from atlas.domain.models.confluence import ConfluenceResult
from atlas.domain.models.enums import Direction
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.market_context import MarketContext
from atlas.domain.models.mtf import MTFAnalysis
from atlas.domain.models.news import NewsFilterStatus
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.smc import SMCAnalysisResult
from atlas.domain.models.strategy import StrategyProfile
from atlas.domain.models.technical import TechnicalAnalysisResult


@dataclass(frozen=True, slots=True)
class ValidationContext:
    """Inputs required to evaluate validation rules."""

    confluence: ConfluenceResult
    mtf: MTFAnalysis
    context: MarketContext
    technical: TechnicalAnalysisResult
    smc: SMCAnalysisResult
    news: NewsFilterStatus
    strategy: StrategyProfile
    trigger_bar: OHLCVBar


@dataclass(frozen=True, slots=True)
class ValidationRuleResult:
    """Result of a single validation rule."""

    rule_name: str
    passed: bool
    reason: str
    enabled: bool


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Aggregate validation outcome."""

    instrument: Instrument
    direction: Direction
    is_valid: bool
    rules: tuple[ValidationRuleResult, ...]
    failed_rules: tuple[str, ...]
    strategy_profile_id: str
    validated_at: datetime
