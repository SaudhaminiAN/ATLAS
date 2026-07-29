"""Confluence service port."""

from typing import Protocol

from atlas.domain.models.confluence import ConfluenceResult
from atlas.domain.models.instrument import Instrument
from atlas.domain.models.market_context import MarketContext
from atlas.domain.models.mtf import MTFAnalysis
from atlas.domain.models.news import NewsFilterStatus
from atlas.domain.models.price_action import PriceActionResult
from atlas.domain.models.smc import SMCAnalysisResult
from atlas.domain.models.strategy import StrategyProfile
from atlas.domain.models.technical import TechnicalAnalysisResult


class ConfluenceServiceProtocol(Protocol):
    """Aggregate analysis module evidence into a confluence score."""

    def calculate(
        self,
        instrument: Instrument,
        mtf: MTFAnalysis,
        technical: TechnicalAnalysisResult,
        smc: SMCAnalysisResult,
        price_action: PriceActionResult,
        context: MarketContext,
        news_status: NewsFilterStatus,
        strategy: StrategyProfile,
    ) -> ConfluenceResult: ...
