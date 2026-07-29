"""No-op pipeline dedupe for backtesting."""

from datetime import datetime

from atlas.domain.models.enums import Timeframe


class NoOpDedupeCache:
    """Always acquire — allows replaying the same bar many times."""

    async def try_acquire(
        self,
        symbol: str,
        timeframe: Timeframe,
        open_time: datetime,
    ) -> bool:
        return True
