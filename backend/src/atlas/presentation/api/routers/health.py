"""Health and readiness endpoints."""

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from atlas.infrastructure.cache.redis_client import check_redis
from atlas.infrastructure.persistence.database import check_database
from atlas.presentation.api.schemas import ApiEnvelope, ApiError

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request) -> ApiEnvelope[dict[str, str | bool]]:
    """Liveness probe — process is running."""
    settings = request.app.state.settings
    return ApiEnvelope(
        success=True,
        data={
            "status": "ok",
            "auth_enabled": settings.auth_enabled,
            "auth_registration_enabled": settings.auth_registration_enabled,
        },
    )


@router.get("/ready")
async def ready(request: Request) -> JSONResponse:
    """Readiness probe — database and Redis must be reachable."""
    container = request.app.state.container
    db_ok = await check_database(container.engine)
    redis_ok = await check_redis(container.redis)

    if db_ok and redis_ok:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=ApiEnvelope(
                success=True,
                data={"database": "ok", "redis": "ok"},
            ).model_dump(mode="json"),
        )

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=ApiEnvelope(
            success=False,
            data=None,
            error=ApiError(
                code="NOT_READY",
                message="One or more dependencies are unavailable",
                details=[
                    {"database": "ok" if db_ok else "unavailable"},
                    {"redis": "ok" if redis_ok else "unavailable"},
                ],
            ),
        ).model_dump(mode="json"),
    )
