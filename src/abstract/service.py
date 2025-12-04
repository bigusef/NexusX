"""Base service class for domain services.

Provides a base class that domain services should inherit from.
"""


class Service:
    """Base service for domain business logic.

    This class serves as a marker base class for all domain services,
    enabling consistent patterns across the codebase.

    Usage with FastAPI (automatic dependency injection):
        ```python
        from typing import Annotated
        from fastapi import Depends

        class AuthService(Service):
            def __init__(
                self,
                user_repo: Annotated[UserRepository, Depends()],
                jwt_service: Annotated[JWTService, Depends()],
            ) -> None:
                self._user_repo = user_repo
                self._jwt_service = jwt_service

        @app.post("/auth/refresh")
        async def refresh(auth_service: Annotated[AuthService, Depends()]):
            return await auth_service.refresh_tokens(token)
        ```

    Usage with ARQ workers (manual instantiation):
        ```python
        async def process_auth_task(ctx: dict, user_id: UUID):
            async with get_session_context() as session:
                async with get_redis_context() as redis:
                    user_repo = UserRepository(session)
                    jwt_service = JWTService(redis)
                    auth_service = AuthService(user_repo, jwt_service)
                    await auth_service.logout_all_devices(user_id)
        ```
    """

    pass
