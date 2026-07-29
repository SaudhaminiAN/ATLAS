"""Multi-timeframe analysis port."""

from typing import Protocol

from atlas.domain.models.enums import Timeframe
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.mtf import MTFAnalysis
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.smc import SMCAnalysisResult
from atlas.domain.models.strategy import StrategyProfile
from atlas.domain.models.technical import TechnicalAnalysisResult


class MultiTimeframeAnalysisServiceProtocol(Protocol):
    """Analyze alignment across strategy timeframes."""

    def analyze(
        self,
        instrument: Instrument,
        timeframe_bars: dict[Timeframe, list[OHLCVBar]],
        smc_results: dict[Timeframe, SMCAnalysisResult | None],
        technical_results: dict[Timeframe, TechnicalAnalysisResult | None],
        strategy: StrategyProfile,
    ) -> MTFAnalysis:
        """Compute MTF alignment from per-TF inputs."""
        ...
