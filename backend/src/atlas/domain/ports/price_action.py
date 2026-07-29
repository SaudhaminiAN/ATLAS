"""Price action service port."""

from typing import Protocol

from atlas.domain.models.enums import Timeframe
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.ohlcv import OHLCVBar
from atlas.domain.models.price_action import PriceActionResult
from atlas.domain.models.price_level import PriceLevel
from atlas.domain.models.smc import SMCAnalysisResult


class PriceActionServiceProtocol(Protocol):
    """Detect candlestick patterns at key levels."""

    def analyze(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        bars: list[OHLCVBar],
        key_levels: list[PriceLevel],
        smc: SMCAnalysisResult,
    ) -> PriceActionResult: ...
