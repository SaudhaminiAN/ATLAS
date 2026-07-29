"""Prompt construction and guardrails for AI explanations (Spec 15)."""

from __future__ import annotations

import json
from typing import Any

from atlas.domain.models.decision import TradingDecision
from atlas.domain.models.enums import Direction

SYSTEM_PROMPT = """You are ATLAS, an institutional trading analysis assistant.

Rules (mandatory):
- Explain ONLY the provided decision snapshot. Do not invent data.
- Do NOT predict future prices or give trade recommendations.
- Do NOT suggest entries, exits, or position sizing beyond what the snapshot shows.
- For WAIT decisions, cite the specific blocking rule, threshold, or news window.
- For BUY/SELL decisions, summarize supporting evidence and validation outcome.
- Keep the response to 3–5 clear sentences in plain English.
"""


def build_prompt_payload(decision: TradingDecision) -> dict[str, Any]:
    """Build JSON payload from stored snapshots only (no live re-fetch)."""
    evidence: list[dict[str, Any]] = []
    if decision.confluence_snapshot is not None:
        evidence = [
            {
                "source": item.source,
                "score": float(item.score),
                "direction": item.direction.value,
            }
            for item in decision.confluence_snapshot.evidence[:12]
        ]

    failed_rules: list[str] = []
    if decision.validation_snapshot is not None:
        failed_rules = list(decision.validation_snapshot.failed_rules)

    news_blocked = False
    if decision.news_status is not None:
        news_blocked = decision.news_status.is_blocked

    return {
        "symbol": decision.instrument.symbol,
        "direction": decision.direction.value,
        "reason": decision.reason,
        "confluence_score": float(decision.confluence_score),
        "evidence": evidence,
        "failed_rules": failed_rules,
        "news_blocked": news_blocked,
        "risk": decision.risk_snapshot,
    }


def build_prompt(decision: TradingDecision) -> str:
    """Full prompt: system guardrails + decision snapshot JSON."""
    payload = build_prompt_payload(decision)
    user_json = json.dumps(payload, indent=2, sort_keys=True)
    return f"{SYSTEM_PROMPT.strip()}\n\n---\nDecision data:\n{user_json}"


def validate_guardrails(prompt: str) -> bool:
    """Return True when required guardrail phrases are present."""
    required = (
        "do not predict",
        "wait decisions",
        "decision snapshot",
    )
    lowered = prompt.lower()
    return all(phrase in lowered for phrase in required)


def mock_explanation_from_payload(payload: dict[str, Any]) -> str:
    """Deterministic explanation for mock provider and tests."""
    direction = payload.get("direction", "WAIT")
    reason = payload.get("reason", "Unknown")
    score = payload.get("confluence_score", 0)
    symbol = payload.get("symbol", "XAUUSD")

    if direction == Direction.WAIT.value:
        failed = payload.get("failed_rules") or []
        if payload.get("news_blocked"):
            return (
                f"ATLAS issued WAIT on {symbol} because a high-impact news window is active. "
                f"The system blocks new trades during this period. "
                f"Confluence score was {score:.2f}. "
                f"Primary reason recorded: {reason}."
            )
        if failed:
            rules = ", ".join(failed)
            return (
                f"ATLAS issued WAIT on {symbol} because validation failed: {rules}. "
                f"Confluence score was {score:.2f}. "
                f"Until these rules pass, no trade is allowed."
            )
        return (
            f"ATLAS issued WAIT on {symbol}. {reason}. "
            f"Confluence score {score:.2f} did not meet actionable criteria."
        )

    evidence = payload.get("evidence") or []
    sources = ", ".join(item["source"] for item in evidence[:3]) or "multiple modules"
    return (
        f"ATLAS issued {direction} on {symbol} with confluence {score:.2f}. "
        f"Validation passed and key evidence came from {sources}. "
        f"Recorded reason: {reason}."
    )
