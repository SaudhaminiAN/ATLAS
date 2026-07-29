"""Authentication REST endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request

from atlas.application.auth.service import AuthError
from atlas.domain.models.user import User
from atlas.presentation.api.dependencies.auth import get_current_user
from atlas.presentation.api.dtos.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from atlas.presentation.api.schemas import ApiEnvelope

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_dto(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        is_active=user.is_active,
        created_at=user.created_at,
    )


def _token_dto(tokens) -> TokenResponse:
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
    )


@router.post("/register")
async def register(request: Request, body: RegisterRequest) -> ApiEnvelope[UserResponse]:
    """Create a new user account."""
    settings = request.app.state.settings
    if not settings.auth_enabled:
        raise HTTPException(status_code=503, detail="Authentication is not enabled")
    service = request.app.state.container.auth_service
    try:
        user = await service.register(body.email, body.password)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiEnvelope(success=True, data=_user_dto(user))


@router.post("/login")
async def login(request: Request, body: LoginRequest) -> ApiEnvelope[TokenResponse]:
    """Authenticate and receive JWT tokens."""
    settings = request.app.state.settings
    if not settings.auth_enabled:
        raise HTTPException(status_code=503, detail="Authentication is not enabled")
    service = request.app.state.container.auth_service
    try:
        _, tokens = await service.login(body.email, body.password)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return ApiEnvelope(success=True, data=_token_dto(tokens))


@router.post("/refresh")
async def refresh_tokens(request: Request, body: RefreshRequest) -> ApiEnvelope[TokenResponse]:
    """Exchange a refresh token for a new access token."""
    settings = request.app.state.settings
    if not settings.auth_enabled:
        raise HTTPException(status_code=503, detail="Authentication is not enabled")
    service = request.app.state.container.auth_service
    try:
        tokens = await service.refresh(body.refresh_token)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return ApiEnvelope(success=True, data=_token_dto(tokens))


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)) -> ApiEnvelope[UserResponse]:
    """Return the authenticated user profile."""
    return ApiEnvelope(success=True, data=_user_dto(user))
