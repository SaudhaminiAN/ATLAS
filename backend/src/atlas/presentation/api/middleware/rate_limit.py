"""Optional Redis-backed rate limiting for API routes."""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from atlas.infrastructure.cache.api_rate_limit import ApiRateLimiter
from atlas.presentation.api.schemas import ApiEnvelope, ApiError

_EXEMPT_PATHS = frozenset(
    {
        "/api/v1/health",
        "/api/v1/ready",
    }
)

_AUTH_PATHS = frozenset(
    {
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/refresh",
    }
)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _rate_limit_response(retry_after: int) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        headers={"Retry-After": str(retry_after)},
        content=ApiEnvelope(
            success=False,
            data=None,
            error=ApiError(
                code="RATE_LIMITED",
                message="Too many requests. Please try again later.",
            ),
        ).model_dump(mode="json"),
    )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply per-IP or per-user request limits when rate limiting is enabled."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = request.app.state.settings
        if not settings.rate_limit_enabled:
            return await call_next(request)

        path = request.url.path.rstrip("/") or "/"
        if path in _EXEMPT_PATHS:
            return await call_next(request)

        user = getattr(request.state, "user", None)
        if user is not None:
            client_key = f"user:{user.id}"
            limit = settings.rate_limit_per_minute
        else:
            client_key = f"ip:{_client_ip(request)}"
            limit = (
                settings.rate_limit_auth_per_minute
                if path in _AUTH_PATHS
                else settings.rate_limit_per_minute
            )

        limiter = ApiRateLimiter(request.app.state.container.redis)
        if await limiter.allow(client_key, limit):
            return await call_next(request)

        retry_after = await limiter.retry_after(client_key)
        return _rate_limit_response(retry_after)
