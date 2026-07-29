# ATLAS Vision

## Purpose

**ATLAS** is an institutional-grade AI-powered decision support system for **XAUUSD (Gold)** trading. It analyzes live market data, detects high-probability opportunities, rejects poor-quality setups, manages risk automatically, and explains every decision.

ATLAS is **not** an autonomous profit generator. It assists traders before, during, and after trades while maintaining a strict preference for **WAIT** over forcing BUY or SELL signals.

## Core Capabilities

- Analyze live and historical market data
- Detect high-probability trading opportunities using objective evidence
- Reject trades that fail deterministic validation rules
- Calculate position size, stop-loss, and take-profit automatically
- Assist throughout the trade lifecycle (pre-entry, in-trade, post-trade)
- Explain every decision in plain language
- Record every trade in a structured journal
- Produce performance analytics and audit trails

## Trading Philosophy

Trading decisions are based on objective evidence from three pillars:

1. **Technical Analysis** — structure, levels, momentum context
2. **Smart Money Concepts (SMC)** — liquidity, order blocks, market structure shifts
3. **Price Action** — candlestick patterns, rejection, displacement

Indicators provide **context only**. Signals must never be generated from indicators alone.

Every trade must pass deterministic validation rules before the Decision Engine emits anything other than WAIT.

## AI Role

The AI layer **explains** decisions. It does **not** make them.

- Never invent trading rules
- Never fabricate market data
- Never override deterministic trading logic
- Never promise profitability or predict future prices

## Supported Instruments

Version 1 supports **XAUUSD only**. Architecture must allow additional instruments without changing core domain logic.

## Design Principles

- Correctness over speed of delivery
- Modularity, readability, and testability over cleverness
- WAIT is the default; conviction must be earned through confluence
- Every decision is auditable and reproducible
- Software maintainable by a professional engineering team

## Accuracy Commitment

Accurate analysis is defined as **reproducible, evidence-based, and measurable** — not as guaranteed price prediction. See [Accuracy Principles](accuracy_principles.md) for full definitions, deterministic rule requirements, and review cadence.

## Implementation Approach

Development follows a phased roadmap — analysis quality is proven via backtesting before live execution. See [MVP Roadmap](mvp_roadmap.md).
