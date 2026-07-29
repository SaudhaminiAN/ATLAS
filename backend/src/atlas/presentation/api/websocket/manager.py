"""WebSocket connection manager."""

import asyncio
import json
from collections import defaultdict

from fastapi import WebSocket

from atlas.domain.events.base import DomainEvent


class WebSocketManager:
    """Manage WebSocket subscriptions by channel."""

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, channel: str, websocket: WebSocket) -> None:
        """Accept and register connection."""
        await websocket.accept()
        async with self._lock:
            self._connections[channel].add(websocket)

    async def disconnect(self, channel: str, websocket: WebSocket) -> None:
        """Remove connection."""
        async with self._lock:
            self._connections[channel].discard(websocket)

    async def broadcast(self, channel: str, message: dict) -> None:
        """Send message to all subscribers on channel."""
        async with self._lock:
            sockets = list(self._connections.get(channel, set()))

        dead: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                dead.append(ws)

        for ws in dead:
            await self.disconnect(channel, ws)

    def on_decision_emitted(self, event: DomainEvent) -> None:
        """Event bus handler for decision.emitted."""
        symbol = event.payload.get("symbol", "XAUUSD")
        channel = f"decisions.{symbol}"
        message = {
            "channel": channel,
            "event": "decision.emitted",
            "payload": event.payload,
            "timestamp": event.occurred_at.isoformat(),
        }
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(channel, message))
        except RuntimeError:
            pass

    def on_bar_received(self, event: DomainEvent) -> None:
        """Event bus handler for market_data.bar.received."""
        symbol = event.payload.get("symbol", "XAUUSD")
        channel = f"market.{symbol}.bars"
        message = {
            "channel": channel,
            "event": "bar.updated",
            "payload": event.payload,
            "timestamp": event.occurred_at.isoformat(),
        }
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(channel, message))
        except RuntimeError:
            pass

    def on_trade_event(self, event: DomainEvent) -> None:
        """Broadcast position updates to subscribers."""
        symbol = event.payload.get("symbol", "XAUUSD")
        channel = f"positions.{symbol}"
        message = {
            "channel": channel,
            "event": event.event_type,
            "payload": event.payload,
            "timestamp": event.occurred_at.isoformat(),
        }
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(channel, message))
        except RuntimeError:
            pass
