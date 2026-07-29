"""Optional JWT gate for API routes when authentication is enabled."""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from atlas.application.auth.service import AuthError
from atlas.presentation.api.schemas import ApiEnvelope, ApiError

_PUBLIC_PATHS = frozenset(
    {
        "/api/v1/health",
        "/api/v1/ready",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/refresh",
    }
)

_PUBLIC_PREFIXES = (
    "/api/v1/docs",
    "/api/v1/openapi.json",
)


def _is_public_path(path: str) -> bool:
    if path in _PUBLIC_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in _PUBLIC_PREFIXES)


def _unauthorized_response(message: str = "Not authenticated") -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content=ApiEnvelope(
            success=False,
            data=None,
            error=ApiError(code="UNAUTHORIZED", message=message),
        ).model_dump(mode="json"),
    )


class AuthMiddleware(BaseHTTPMiddleware):
    """Require a valid Bearer token on protected routes when auth is enabled."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = request.app.state.settings
        if not settings.auth_enabled:
            return await call_next(request)

        path = request.url.path.rstrip("/") or "/"
        if _is_public_path(path):
            return await call_next(request)

        # WebSocket auth is enforced in the WebSocket route handler.
        if path.endswith("/ws"):
            return await call_next(request)

        authorization = request.headers.get("Authorization", "")
        if not authorization.lower().startswith("bearer "):
            return _unauthorized_response()

        token = authorization[7:].strip()
        if not token:
            return _unauthorized_response()

        service = request.app.state.container.auth_service
        try:
            user_id = service.verify_access_token(token)
            user = await service.get_user(user_id)
        except AuthError:
            return _unauthorized_response("Invalid or expired token")

        if user is None or not user.is_active:
            return _unauthorized_response()

        request.state.user = user
        return await call_next(request)
