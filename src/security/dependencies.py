"""Security dependencies for FastAPI endpoints.

Provides authentication dependencies for protected routes.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer

from src.exceptions import AuthorizationException

from .jwt import JWTService
from .jwt import TokenPayload


# Bearer token security scheme for OpenAPI docs
bearer_scheme = HTTPBearer()


async def _get_token_payload(
    jwt_service: Annotated[JWTService, Depends()],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> TokenPayload:
    """Extract and verify token payload from Authorization header."""
    return await jwt_service.verify_access_token(credentials.credentials)


async def _get_current_user(
    payload: Annotated[TokenPayload, Depends(_get_token_payload)],
) -> UUID:
    """Get current user ID from Authorization header."""
    return payload.sub


async def _get_staff_user(
    payload: Annotated[TokenPayload, Depends(_get_token_payload)],
) -> UUID:
    """Get current user ID, verifying the user is a staff member."""
    if not payload.is_staff:
        raise AuthorizationException()

    return payload.sub


# Type aliases for cleaner endpoint signatures
UserID = Annotated[UUID, Depends(_get_current_user)]
StaffID = Annotated[UUID, Depends(_get_staff_user)]
