# Spec 02 — Market Data

## Objective

Ingest, normalize, persist, and stream OHLCV for XAUUSD. **Analysis accuracy starts here.**

## Scope

### In Scope

- `MarketDataProviderProtocol` + mock provider
- `MarketDataReplayProtocol` for backtesting
- `MarketDataService` — fetch, validate, persist, stream
- Data quality pipeline
- REST, WebSocket, domain events

### Out of Scope

- Tick data, multi-instrument, live broker feed (adapter only)

## Inputs

| Input | Source | Required |
|-------|--------|----------|
| Raw bars | `MarketDataProviderProtocol` | Live mode |
| Historical bars | `ohlcv_bars` / CSV | Replay mode |
| `instrument`, `timeframe`, date range | API / config | Yes |

## Outputs

| Output | Type | Consumers |
|--------|------|-----------|
| `OHLCVBar` | Domain model | All analysis modules |
| `market_data.bar.received` | Event (closed bar only) | Pipeline (20) |
| `market_data.gap.detected` | Event | Logging |
| `BarQualityReport` | Report | Monitoring |
| REST / WebSocket | API | Frontend (21) |

## Interfaces

```python
class MarketDataProviderProtocol(Protocol):
    async def fetch_bars(
        self, instrument: Instrument, timeframe: Timeframe,
        start: datetime, end: datetime,
    ) -> list[OHLCVBar]: ...

    async def subscribe_bars(
        self, instrument: Instrument, timeframe: Timeframe,
    ) -> AsyncIterator[OHLCVBar]: ...

class MarketDataReplayProtocol(Protocol):
    """Used by Spec 16 backtesting."""
    def iter_bars(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> Iterator[OHLCVBar]: ...

    def get_bars_up_to(
        self,
        instrument: Instrument,
        timeframe: Timeframe,
        as_of: datetime,
        limit: int,
    ) -> list[OHLCVBar]: ...

class MarketDataServiceProtocol(Protocol):
    async def ingest_bar(self, bar: OHLCVBar) -> IngestResult: ...
    async def get_latest(self, instrument: Instrument, tf: Timeframe) -> OHLCVBar | None: ...
    async def get_history(self, ...) -> list[OHLCVBar]: ...
```

## Database

| Table / Cache | Operation | Owner |
|---------------|-----------|-------|
| `ohlcv_bars` | INSERT, SELECT | This spec |
| `bars:{symbol}:{tf}:latest` | Redis (TTL 60s) | This spec |

## Data Quality Rules

| Rule | Action on Failure |
|------|-------------------|
| OHLC integrity | Reject |
| Positive prices | Reject |
| UTC timestamps | Normalize |
| Duplicates | Skip insert |
| Outlier (>5× ATR) | Flag `is_outlier`, exclude from analysis |
| Gap in sequence | Log + `market_data.gap.detected` |
| Forming bar | Do not emit event |

## Bar Alignment

UTC boundaries per timeframe (M1–D1). See full table in prior version.

## Domain Models

```python
@dataclass(frozen=True)
class OHLCVBar:
    instrument: Instrument
    timeframe: Timeframe
    open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    is_outlier: bool = False
    quality_flags: list[str] = field(default_factory=list)
```

## Edge Cases

| Case | Behavior |
|------|----------|
| Provider disconnect | Log error; retry with backoff |
| Out-of-order bar | Reject if older than latest persisted |
| Weekend gap | Expected; gap event optional |
| `get_bars_up_to` in replay | Never returns bars with `open_time > as_of` |

## Acceptance Criteria

- [ ] Validation rules unit tested (pass + fail each)
- [ ] Closed bars only trigger event
- [ ] Replay protocol enforces no look-ahead
- [ ] REST + WebSocket + Redis cache
- [ ] Integration test with mock provider + test DB

## Dependencies

- Spec 01

## Downstream Consumers

- Specs 03–07, 16, 20, 21
