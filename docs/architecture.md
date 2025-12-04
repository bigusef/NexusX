# Architecture

This document explains the architectural patterns and design decisions in Nexus Cortex.

## Overview

Nexus Cortex follows **Clean Architecture** principles with **Domain-Driven Design (DDD)** patterns. The codebase is organized into layers with clear separation of concerns.

## Project Structure

```
src/
├── main.py                 # FastAPI application entry point
├── core/                   # Infrastructure layer
│   ├── config.py          # Settings and configuration
│   ├── database.py        # Database connection management
│   ├── redis.py           # Redis connection management
│   ├── jwt.py             # JWT token service
│   ├── i18n.py            # Internationalization
│   ├── middleware.py      # HTTP middleware
│   ├── context.py         # Request context (language, platform)
│   └── events.py          # Lifespan events (startup/shutdown)
├── abstract/               # Base classes and abstractions
│   ├── entity.py          # SQLAlchemy Entity base class
│   ├── repository.py      # Generic Repository base class
│   └── schema.py          # Pydantic schema base class
├── domains/                # Business domains
│   └── auth/              # Authentication domain
│       ├── entities.py    # User entity
│       ├── repositories.py# UserRepository
│       └── services.py    # AuthService
├── routers/                # API routing layer
│   ├── admin/             # Admin platform endpoints
│   └── customer/          # Customer platform endpoints
├── exceptions/             # Custom exception hierarchy
│   ├── base.py            # BaseAppException
│   ├── auth.py            # Authentication exceptions
│   ├── resource.py        # Resource exceptions (404, 409)
│   ├── validation.py      # Validation exceptions
│   └── http.py            # HTTP-related exceptions
└── utilities/              # Shared utilities
    ├── enums.py           # Application enums
    └── parser.py          # Parsing utilities
```

## Core Patterns

### Lazy Initialization

Database and Redis connections use lazy initialization to avoid connection issues during import time:

```python
# Global variable starts as None
_engine: AsyncEngine | None = None

async def init_database() -> None:
    """Initialize on application startup."""
    global _engine
    _engine = create_async_engine(settings.database_url)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency - raises if not initialized."""
    if _engine is None:
        raise RuntimeError("Database not initialized")
    # ... yield session
```

This pattern is used for both database and Redis connections, initialized during the application lifespan startup event.

### Entity Base Class

All database models inherit from `Entity`, which provides:

- Auto-generated primary key (`pk` field maps to `id` column)
- Auto-generated table names (CamelCase → snake_case + 's')
- Consistent naming convention for constraints

```python
from src.abstract import Entity, TimeStampMixin, StatusMixin

class User(Entity, TimeStampMixin, StatusMixin):
    # pk is auto-provided (BigInteger with Identity)
    # __tablename__ auto-generated as "users"

    email: Mapped[str] = mapped_column(String(255), unique=True)
    first_name: Mapped[str] = mapped_column(String(100))
```

**Available Mixins:**
- `TimeStampMixin`: Adds `created_at` and `updated_at` fields
- `StatusMixin`: Adds `is_locked` field and `is_active` property

### Repository Pattern

The generic `Repository[T]` base class provides type-safe CRUD operations:

```python
from src.abstract import Repository
from .entities import User

class UserRepository(Repository[User]):
    # Entity type is auto-detected from generic parameter

    # Add domain-specific methods
    async def select_by_email(self, email: str) -> User | None:
        return await self.select_one(User.email == email)
```

**Available Operations:**
- `get_one(*filters)` - Get entity or raise NotFoundException
- `select_one(*filters)` - Get entity or return None
- `select_all(*filters)` - Get all matching entities
- `paginate(*filters, limit, offset)` - Paginated results with count
- `get_by_id(pk)` - Get by primary key
- `create(**kwargs)` - Create entity
- `bulk_create(entities_data)` - Bulk create
- `update(entity, **kwargs)` - Update entity
- `delete(entity)` - Delete entity
- `count(*filters)` - Count matching entities
- `exists(*filters)` - Check existence

### Service Layer

Services contain business logic and orchestrate between repositories:

```python
class AuthService:
    def __init__(self, user_repository: UserRepository, jwt_service: JWTService):
        self._user_repo = user_repository
        self._jwt_service = jwt_service

    async def refresh_tokens(self, refresh_token: str) -> TokenPair:
        # Verify token, check user exists and is active
        # Return new token pair
```

Services are injected with their dependencies (repositories, other services) rather than raw database sessions.

### Exception Hierarchy

All exceptions inherit from `BaseAppException` and support internationalization:

```
BaseAppException
├── AuthenticationException (401)
├── AuthorizationException (403)
├── InvalidTokenException (401)
├── ExpiredTokenException (401)
├── RevokedTokenException (401)
├── NotFoundException (404)
├── ConflictException (409)
├── ValidationException (422)
├── BusinessRuleException (400)
├── BadRequestException (400)
├── RateLimitException (429)
├── ServiceUnavailableException (503)
└── GoneException (410)
```

Exceptions use lazy translation for i18n support:

```python
from src.core.i18n import lazy_gettext as _

class NotFoundException(BaseAppException):
    status_code = 404
    default_message = _("Resource not found")
```

## Request Flow

```
Request
    ↓
Middleware (X-Source, Accept-Language)
    ↓
Router (endpoint handler)
    ↓
Service (business logic)
    ↓
Repository (data access)
    ↓
Database/Redis
```

### Middleware

`RequestHeadersMiddleware` processes incoming requests to:
- Validate `X-Source` header (admin/customer platform)
- Parse `Accept-Language` header for i18n
- Set request context for downstream use

### Request Context

Request-scoped data (language, platform) is stored using `contextvars`:

```python
from src.core.context import get_language, get_platform

# In any handler or service
current_lang = get_language()  # Returns Language enum
current_platform = get_platform()  # Returns Platform enum
```

## Background Workers

ARQ workers process background jobs asynchronously:

```python
# workers/main.py
class WorkerSettings:
    functions = [ping]  # Register task functions
    redis_settings = RedisSettings(...)
    max_jobs = 10
    job_timeout = 300
```

Workers run as a separate service and share the same codebase but have their own Redis connection.

**Defining Tasks:**
```python
async def my_task(ctx: dict, user_id: UUID):
    async with get_session_context() as session:
        repo = UserRepository(session)
        # ... task logic
        await session.commit()
```

**Enqueueing Jobs:**
```python
await redis.enqueue_job('my_task', user_id)
```

## Internationalization (i18n)

The i18n system uses Babel/gettext with translations loaded at startup:

```python
from src.core.i18n import gettext as _, lazy_gettext

# Immediate translation (in request context)
message = _("Welcome to our platform")

# Lazy translation (for module-level constants)
ERROR_MSG = lazy_gettext("An error occurred")
```

**Supported Languages:** Arabic (ar), German (de), English (en), Spanish (es), French (fr), Italian (it), Russian (ru)

## JWT Authentication

The JWT service provides secure token management:

- **Access tokens**: Short-lived (15m default), contain user claims
- **Refresh tokens**: Long-lived (7d default), used to get new access tokens
- **Token versioning**: Enables "logout all devices" functionality
- **Refresh token rotation**: Old refresh token is revoked on use

```python
# Create tokens
tokens = await jwt_service.create_token_pair(
    user_id=user.pk,
    email=user.email,
    is_staff=user.is_staff,
)

# Verify tokens
payload = await jwt_service.verify_access_token(token)

# Revoke tokens
await jwt_service.revoke_refresh_token(jti)        # Single device
await jwt_service.revoke_all_user_tokens(user_id)  # All devices
```

## Key Design Decisions

1. **Lazy Initialization**: Database and Redis connections are initialized at startup, not import time, preventing connection issues during testing and module loading.

2. **Generic Repository**: The Repository base class uses Python generics for type safety while reducing boilerplate code.

3. **Separate Workers**: ARQ workers run as a separate service, allowing independent scaling and deployment.

4. **Exception i18n**: All exceptions support translation, enabling localized error messages.

5. **No Auto-commit**: Database sessions use explicit transaction control (`autocommit=False`) for predictable behavior.

6. **Platform Separation**: Admin and customer APIs are in separate router modules, allowing different authentication and authorization rules.

7. **UUID for Users**: The User entity uses UUID primary keys instead of auto-increment integers for better distribution and security.
