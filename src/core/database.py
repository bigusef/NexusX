"""Database module.

This module provides async SQLAlchemy engine and session factory
for PostgreSQL connections using asyncpg driver.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import get_settings

settings = get_settings()

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,  # Log SQL queries in debug mode
    future=True,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=10,
    max_overflow=20,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db() -> None:
    """Initialize database connection (called on startup)"""
    # Test connection
    async with engine.begin() as conn:
        # Create tables if needed (in production, use Alembic migrations)
        # from app.abstract.entity import Entity
        # await conn.run_sync(Entity.metadata.create_all)
        pass


async def close_db() -> None:
    """Close database connection (called on shutdown)"""
    await engine.dispose()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide async database session for dependency injection.

    Yields:
        AsyncSession instance that auto-closes after use.

    Example:
        @app.get("/users")
        async def get_users(session: AsyncSession = Depends(get_session)):
            result = await session.execute(select(User))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
