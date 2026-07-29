"""WebSocket routes."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from atlas.application.auth.service import AuthError

router = APIRouter(tags=["websocket"])


async def _authorize_websocket(websocket: WebSocket) -> bool:
    settings = websocket.app.state.settings
    if not settings.auth_enabled:
        return True

    token = websocket.query_params.get("access_token", "").strip()
    if not token:
        return False

    service = websocket.app.state.container.auth_service
    try:
        user_id = service.verify_access_token(token)
        user = await service.get_user(user_id)
    except AuthError:
        return False

    return user is not None and user.is_active


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket entry — subscribe via ?channel=market.XAUUSD.bars."""
    if not await _authorize_websocket(websocket):
        await websocket.close(code=4401)
        return

    channel = websocket.query_params.get("channel", "market.XAUUSD.bars")
    manager = websocket.app.state.ws_manager

    await manager.connect(channel, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(channel, websocket)
