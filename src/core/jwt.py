"""JWT token generation and verification service.

Provides secure access and refresh token handling with Redis-based
revocation support for both single-device and all-device logout.
"""

from datetime import UTC
from datetime import datetime
from typing import Annotated
from uuid import UUID
from uuid import uuid4

import redis.asyncio as aioredis
from fastapi import Depends
from jose import JWTError
from jose import jwt
from pydantic import BaseModel
from pydantic import Field

from src.core import settings
from src.core.redis import get_redis
from src.exceptions import ExpiredTokenException
from src.exceptions import InvalidTokenException
from src.exceptions import RevokedTokenException


class TokenPayload(BaseModel):
    """Decoded token payload with validated fields."""

    sub: UUID = Field(description="User ID")
    type: str = Field(description="Token type: 'access' or 'refresh'")
    version: int = Field(description="Token version for revocation")
    exp: int = Field(description="Expiration timestamp")
    iat: int = Field(description="Issued at timestamp")
    jti: UUID | None = Field(default=None, description="Token unique ID (refresh only)")
    email: str | None = Field(default=None, description="User email (access only)")
    is_staff: bool | None = Field(default=None, description="Staff status (access only)")


class TokenPair(BaseModel):
    """Token pair containing access and refresh tokens."""

    access: str = Field(description="JWT access token")
    refresh: str = Field(description="JWT refresh token")


class JWTService:
    """JWT token generation and verification service.

    Handles creation and verification of access and refresh tokens.
    Uses Redis for token versioning and revocation tracking.

    Security features:
    - Token versioning for "logout all devices" functionality
    - Individual refresh token revocation via Redis
    - Separate access/refresh token types to prevent misuse
    - Short-lived access tokens, long-lived refresh tokens

    Usage with FastAPI (automatic dependency injection):
        ```python
        from typing import Annotated
        from fastapi import Depends

        @app.post("/login")
        async def login(
            jwt_service: Annotated[JWTService, Depends()],
        ):
            tokens = await jwt_service.create_token_pair(
                user_id=user.pk,
                email=user.email,
                is_staff=user.is_staff,
            )
            return tokens
        ```

    Usage with ARQ workers (manual instantiation):
        ```python
        async def process_token_task(ctx: dict, user_id: UUID):
            async with get_redis_context() as redis:
                jwt_service = JWTService(redis)
                await jwt_service.revoke_all_user_tokens(user_id)
        ```

    Token operations:
        ```python
        # Verify tokens
        payload = await jwt_service.verify_access_token(tokens.access)
        payload = await jwt_service.verify_refresh_token(tokens.refresh)

        # Revoke tokens
        await jwt_service.revoke_refresh_token(jti)  # Single device
        await jwt_service.revoke_all_user_tokens(user_id)  # All devices
        ```
    """

    # Redis key prefixes
    _TOKEN_VERSION_PREFIX = "jwt:version:"
    _REFRESH_TOKEN_PREFIX = "jwt:refresh:"

    def __init__(self, redis: Annotated[aioredis.Redis, Depends(get_redis)]) -> None:
        """Initialize JWT service with Redis client.

        Args:
            redis: Redis client for token management.
        """
        self._redis = redis
        self._secret_key = settings.jwt.secret_key.get_secret_value()
        self._algorithm = settings.jwt.algorithm
        self._access_expiration = settings.jwt.access_expiration
        self._refresh_expiration = settings.jwt.refresh_expiration

    # =========================================================================
    # TOKEN VERSION MANAGEMENT
    # =========================================================================

    async def _get_token_version(self, user_id: UUID) -> int:
        """Get current token version for a user.

        Args:
            user_id: User UUID.

        Returns:
            Current token version (0 if not set).
        """
        key = f"{self._TOKEN_VERSION_PREFIX}{user_id}"
        version = await self._redis.get(key)
        return int(version) if version else 0

    async def _increment_token_version(self, user_id: UUID) -> int:
        """Increment token version, invalidating all existing tokens.

        Args:
            user_id: User UUID.

        Returns:
            New token version.
        """
        key = f"{self._TOKEN_VERSION_PREFIX}{user_id}"
        return await self._redis.incr(key)

    # =========================================================================
    # REFRESH TOKEN TRACKING
    # =========================================================================

    async def _store_refresh_token(self, jti: UUID, user_id: UUID) -> None:
        """Store refresh token as active in Redis.

        Args:
            jti: Refresh token unique ID.
            user_id: User UUID.
        """
        key = f"{self._REFRESH_TOKEN_PREFIX}{jti}"
        ttl = int(self._refresh_expiration.total_seconds())
        await self._redis.setex(key, ttl, str(user_id))

    async def _is_refresh_token_active(self, jti: str | UUID) -> bool:
        """Check if refresh token is still active.

        Args:
            jti: Refresh token unique ID.

        Returns:
            True if active, False if revoked or expired.
        """
        key = f"{self._REFRESH_TOKEN_PREFIX}{jti}"
        return await self._redis.exists(key) > 0

    # =========================================================================
    # TOKEN CREATION
    # =========================================================================

    def _create_access_token(
        self,
        user_id: UUID,
        email: str,
        is_staff: bool,
        version: int,
    ) -> str:
        """Create a JWT access token.

        Args:
            user_id: User UUID.
            email: User email address.
            is_staff: Whether user is staff/admin.
            version: Token version for invalidation.

        Returns:
            Encoded JWT access token.
        """
        now = datetime.now(UTC)
        exp = now + self._access_expiration

        payload = {
            "sub": str(user_id),
            "email": email,
            "is_staff": is_staff,
            "version": version,
            "type": "access",
            "exp": int(exp.timestamp()),
            "iat": int(now.timestamp()),
        }

        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    async def _create_refresh_token(self, user_id: UUID, version: int) -> str:
        """Create a JWT refresh token and store in Redis.

        Args:
            user_id: User UUID.
            version: Token version for invalidation.

        Returns:
            Encoded JWT refresh token.
        """
        now = datetime.now(UTC)
        exp = now + self._refresh_expiration
        jti = uuid4()

        payload = {
            "sub": str(user_id),
            "version": version,
            "jti": str(jti),
            "type": "refresh",
            "exp": int(exp.timestamp()),
            "iat": int(now.timestamp()),
        }

        token = jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

        # Store refresh token as active in Redis
        await self._store_refresh_token(jti, user_id)

        return token

    async def create_token_pair(
        self,
        user_id: UUID,
        email: str,
        is_staff: bool,
    ) -> TokenPair:
        """Create both access and refresh tokens.

        Args:
            user_id: User UUID.
            email: User email address.
            is_staff: Whether user is staff/admin.

        Returns:
            TokenPair with access and refresh tokens.
        """
        version = await self._get_token_version(user_id)
        access_token = self._create_access_token(user_id, email, is_staff, version)
        refresh_token = await self._create_refresh_token(user_id, version)

        return TokenPair(access=access_token, refresh=refresh_token)

    # =========================================================================
    # TOKEN VERIFICATION
    # =========================================================================

    def _decode_token(self, token: str) -> dict:
        """Decode and verify JWT token signature and expiration.

        Args:
            token: JWT token string.

        Returns:
            Decoded token payload.

        Raises:
            InvalidTokenException: If token is malformed or invalid signature.
            ExpiredTokenException: If token has expired.
        """
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise ExpiredTokenException() from None
        except JWTError:
            raise InvalidTokenException() from None

    async def verify_access_token(self, token: str) -> TokenPayload:
        """Verify access token and return payload.

        Args:
            token: JWT access token.

        Returns:
            Validated token payload.

        Raises:
            InvalidTokenException: If token is not an access token.
            ExpiredTokenException: If token has expired.
            RevokedTokenException: If token version is outdated.
        """
        payload = self._decode_token(token)

        # Verify token type
        if payload.get("type") != "access":
            raise InvalidTokenException()

        # Verify token version
        user_id = UUID(payload["sub"])
        current_version = await self._get_token_version(user_id)

        if payload.get("version", 0) != current_version:
            raise RevokedTokenException()

        return TokenPayload(**payload)

    async def verify_refresh_token(self, token: str) -> TokenPayload:
        """Verify refresh token and return payload.

        Args:
            token: JWT refresh token.

        Returns:
            Validated token payload.

        Raises:
            InvalidTokenException: If token is not a refresh token.
            ExpiredTokenException: If token has expired.
            RevokedTokenException: If token is revoked or version outdated.
        """
        payload = self._decode_token(token)

        # Verify token type
        if payload.get("type") != "refresh":
            raise InvalidTokenException()

        # Verify token version
        user_id = UUID(payload["sub"])
        current_version = await self._get_token_version(user_id)

        if payload.get("version", 0) != current_version:
            raise RevokedTokenException()

        # Verify token is still active in Redis
        jti = payload.get("jti")
        if not jti or not await self._is_refresh_token_active(jti):
            raise RevokedTokenException()

        return TokenPayload(**payload)

    # =========================================================================
    # TOKEN REFRESH
    # =========================================================================

    async def refresh_token_pair(self, refresh_token: str, email: str, is_staff: bool) -> TokenPair:
        """Create a new access token using a valid refresh token.

        This method:
        1. Verifies the refresh token is valid and not revoked
        2. Creates a new access token
        3. If refresh token expires within 2x access token lifetime, rotates it
        4. Otherwise, returns the original refresh token

        Note: The auth service should validate that the user still exists
        and is active before calling this method.

        Args:
            refresh_token: Current refresh token.
            email: User email address (from database).
            is_staff: Whether user is staff/admin (from database).

        Returns:
            TokenPair with new access token and (possibly rotated) refresh token.

        Raises:
            InvalidTokenException: If token is invalid.
            ExpiredTokenException: If token has expired.
            RevokedTokenException: If token is revoked.
        """
        payload = await self.verify_refresh_token(refresh_token)

        version = await self._get_token_version(payload.sub)
        access_token = self._create_access_token(payload.sub, email, is_staff, version)

        # Check if the refresh token needs rotation
        # Rotate if remaining time < 2 * access token expiration
        now = datetime.now(UTC)
        refresh_exp = datetime.fromtimestamp(payload.exp, tz=UTC)
        remaining_time = refresh_exp - now
        rotation_threshold = self._access_expiration * 2

        if remaining_time < rotation_threshold:
            # Revoke old refresh token and create new one
            if payload.jti:
                await self.revoke_refresh_token(payload.jti)

            new_refresh_token = await self._create_refresh_token(payload.sub, version)
            return TokenPair(access=access_token, refresh=new_refresh_token)

        return TokenPair(access=access_token, refresh=refresh_token)

    # =========================================================================
    # TOKEN REVOCATION
    # =========================================================================

    async def revoke_refresh_token(self, jti: str | UUID) -> None:
        """Revoke a specific refresh token (single device logout).

        Args:
            jti: Refresh token unique ID.
        """
        key = f"{self._REFRESH_TOKEN_PREFIX}{jti}"
        await self._redis.delete(key)

    async def revoke_all_user_tokens(self, user_id: UUID) -> None:
        """Revoke all tokens for a user (all devices logout).

        Increments the user's token version, invalidating all existing tokens.

        Args:
            user_id: User UUID.
        """
        await self._increment_token_version(user_id)
