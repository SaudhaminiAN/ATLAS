"""CLI entry point for backtesting (Spec 16)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime

from atlas.application.container import build_container
from atlas.domain.models.backtest import BacktestConfig, BacktestResult
from atlas.domain.models.enums import Timeframe
from atlas.infrastructure.cache.redis_client import create_redis
from atlas.infrastructure.config import get_settings
from atlas.infrastructure.logging import configure_logging
from atlas.infrastructure.persistence.database import create_engine


def _result_to_dict(result: BacktestResult) -> dict:
    return {
        "symbol": result.symbol,
        "timeframe": result.timeframe.value,
        "start": result.start.isoformat(),
        "end": result.end.isoformat(),
        "bars_processed": result.bars_processed,
        "pipeline_runs": result.pipeline_runs,
        "completed_runs": result.completed_runs,
        "skipped_runs": result.skipped_runs,
        "failed_runs": result.failed_runs,
        "decision_counts": [
            {"direction": item.direction.value, "count": item.count}
            for item in result.decision_counts
        ],
        "wait_reasons": [
            {"reason": reason, "count": count}
            for reason, count in result.wait_reasons
        ],
        "module_accuracy": [
            {
                "source": item.source,
                "appearances": item.appearances,
                "actionable_appearances": item.actionable_appearances,
            }
            for item in result.module_accuracy
        ],
        "duration_ms": result.duration_ms,
    }


async def _run_cli(args: argparse.Namespace) -> BacktestResult:
    settings = get_settings()
    configure_logging(settings)
    engine = create_engine(settings)
    redis = await create_redis(settings.redis_url)
    try:
        container = build_container(settings, engine, redis)
        config = BacktestConfig(
            symbol=args.symbol.upper(),
            timeframe=Timeframe(args.timeframe),
            start=args.start,
            end=args.end,
            persist_decisions=args.persist_decisions,
            persist_pipeline_runs=args.persist_pipeline_runs,
            risk_enabled=args.risk_enabled,
        )
        return await container.backtest_runner.run(config)
    finally:
        await redis.aclose()
        await engine.dispose()


def _parse_datetime(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def main() -> None:
    """Run backtest from command line and print JSON report."""
    parser = argparse.ArgumentParser(description="ATLAS historical backtest replay")
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="M15")
    parser.add_argument("--start", required=True, type=_parse_datetime)
    parser.add_argument("--end", required=True, type=_parse_datetime)
    parser.add_argument("--persist-decisions", action="store_true")
    parser.add_argument("--persist-pipeline-runs", action="store_true")
    parser.add_argument("--risk-enabled", action="store_true")
    args = parser.parse_args()

    if args.end < args.start:
        print(json.dumps({"error": "end must be >= start"}), file=sys.stderr)
        sys.exit(1)

    try:
        result = asyncio.run(_run_cli(args))
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)

    print(json.dumps(_result_to_dict(result), indent=2))


if __name__ == "__main__":
    main()
