"""Auth dependencies for protected routes."""

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from atlas.application.auth.service import AuthError, AuthService
from atlas.domain.models.user import User

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> User:
    """Require a valid JWT access token when auth is enabled."""
    settings = request.app.state.settings
    if not settings.auth_enabled:
        raise HTTPException(
            status_code=503,
            detail="Authentication is not enabled on this server",
        )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Not authenticated")

    service: AuthService = request.app.state.container.auth_service
    try:
        user_id = service.verify_access_token(credentials.credentials)
        user = await service.get_user(user_id)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
