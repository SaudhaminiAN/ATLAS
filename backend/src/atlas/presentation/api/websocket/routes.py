"""WebSocket routes."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket entry — subscribe via ?channel=market.XAUUSD.bars."""
    channel = websocket.query_params.get("channel", "market.XAUUSD.bars")
    manager = websocket.app.state.ws_manager

    await manager.connect(channel, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(channel, websocket)
