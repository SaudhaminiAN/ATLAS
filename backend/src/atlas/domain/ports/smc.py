"""SMC analysis port."""

from typing import Protocol

from atlas.domain.models.enums import Timeframe
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.smc import SMCAnalysisResult


class SmartMoneyConceptsServiceProtocol(Protocol):
    """Smart money concepts analysis service."""

    def analyze(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        bars: list[OHLCVBar],
    ) -> SMCAnalysisResult:
        """Run SMC analysis on bar history."""
        ...
