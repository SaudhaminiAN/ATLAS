"""Technical analysis port."""

from typing import Protocol

from atlas.domain.models.enums import Timeframe
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.swing import SwingPoint
from atlas.domain.models.technical import TechnicalAnalysisResult


class SwingDetectorProtocol(Protocol):
    """Shared swing detection utility."""

    def detect_swings(self, bars: list[OHLCVBar], lookback: int) -> list[SwingPoint]:
        """Detect swing points in bar history."""
        ...


class TechnicalAnalysisServiceProtocol(Protocol):
    """Technical analysis service."""

    def analyze(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        bars: list[OHLCVBar],
    ) -> TechnicalAnalysisResult:
        """Run technical analysis on bar history."""
        ...
