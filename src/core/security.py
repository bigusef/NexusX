"""Security dependencies for FastAPI."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer

from src.core.jwt import JWTService
from src.core.jwt import TokenPayload
from src.exceptions import AuthorizationException


# Bearer token security scheme for OpenAPI docs
bearer_scheme = HTTPBearer()


async def _get_token_payload(
        jwt_service: Annotated[JWTService, Depends()],
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> TokenPayload:
    """Extract and verify token payload from Authorization header.

    Args:
        jwt_service: JWT service for token verification.
        credentials: Bearer token credentials from HTTPBearer security scheme.

    Returns:
        TokenPayload with user information.

    Raises:
        InvalidTokenException: If token is invalid.
        ExpiredTokenException: If token has expired.
        RevokedTokenException: If token is revoked.
    """
    return await jwt_service.verify_access_token(credentials.credentials)


async def get_current_user(
        payload: Annotated[TokenPayload, Depends(_get_token_payload)],
) -> UUID:
    """Get current user ID from Authorization header.

    Args:
        payload: Token payload from dependency injection.

    Returns:
        User ID as UUID.
    """
    return payload.sub


async def get_staff_user(
        payload: Annotated[TokenPayload, Depends(_get_token_payload)],
) -> UUID:
    """Get current user ID, verifying the user is a staff member.

    Args:
        payload: Token payload from dependency injection.

    Returns:
        User ID as UUID if user is staff.

    Raises:
        AuthorizationException: If user is not staff.
    """
    if not payload.is_staff:
        raise AuthorizationException()

    return payload.sub


# Type aliases for cleaner endpoint signatures
UserID = Annotated[UUID, Depends(get_current_user)]
StaffID = Annotated[UUID, Depends(get_staff_user)]
