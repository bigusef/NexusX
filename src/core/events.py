"""Application lifespan events module.

This module provides lifespan management for startup and shutdown events.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.database import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application lifespan events.

    Handles startup and shutdown tasks:
    - Startup: Initialize database connection
    - Shutdown: Close database connection and cleanup resources

    Args:
        app: FastAPI application instance.

    Yields:
        None after startup tasks complete.
    """
    # Startup
    await init_db()

    yield

    # Shutdown
    await close_db()
