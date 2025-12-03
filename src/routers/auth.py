"""Authentication API routes for the root application."""

from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import status
from pydantic import BaseModel
from pydantic import Field

from src.core.security import UserID
from src.domains.auth.services import AuthService
from src.domains.auth.services import TokenPair


# ─── Schemas ──────────────────────────────────────────────────────────────────


class RefreshTokenRequest(BaseModel):
    """Request schema for token refresh and logout endpoints."""

    refresh_token: str = Field(..., min_length=1, description="JWT refresh token")


# ─── Router ───────────────────────────────────────────────────────────────────


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/refresh",
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Exchange a valid refresh token for a new token pair.",
    responses={
        200: {"description": "New token pair returned successfully"},
        401: {"description": "Invalid, expired, or revoked refresh token"},
    },
)
async def refresh_tokens(
        request: RefreshTokenRequest,
        auth_service: Annotated[AuthService, Depends()],
) -> TokenPair:
    """Refresh access token using a valid refresh token.

    This endpoint:
    1. Verifies the refresh token is valid and not revoked
    2. Validates the user still exists and is active
    3. Returns a new access token
    4. May rotate the refresh token if nearing expiration
    """
    return await auth_service.refresh_tokens(request.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout from current device",
    description="Revoke the provided refresh token to logout from current device.",
    responses={
        204: {"description": "Logout successful, no content returned"},
        401: {"description": "Invalid or expired refresh token"},
    },
)
async def logout(
        request: RefreshTokenRequest,
        auth_service: Annotated[AuthService, Depends()],
) -> None:
    """Logout from the current device by revoking the refresh token.

    After calling this endpoint, the provided refresh token will no longer
    be valid for obtaining new access tokens. The access token remains
    valid until it expires.
    """
    await auth_service.logout(request.refresh_token)


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout from all devices",
    description="Invalidate all tokens for the current user, logging out from all devices.",
    responses={
        204: {"description": "All sessions terminated, no content returned"},
        401: {"description": "Invalid or expired access token"},
    },
)
async def logout_all_devices(
        user_id: UserID,
        auth_service: Annotated[AuthService, Depends()],
) -> None:
    """Logout from all devices by invalidating all user tokens.

    This increments the user's token version, making all existing
    access and refresh tokens invalid immediately.
    """
    await auth_service.logout_all_devices(user_id)
