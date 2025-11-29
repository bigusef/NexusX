"""Application lifespan events module.

This module provides lifespan management for startup and shutdown events.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .database import close_database
from .database import init_database
from .i18n import init_translations
from .redis import close_redis
from .redis import init_redis


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application lifespan events.

    Handles startup and shutdown tasks:
    - Startup: Initialize database and Redis connections
    - Shutdown: Close database and Redis connections

    Args:
        app: FastAPI application instance.

    Yields:
        None after startup tasks complete.
    """
    # Startup
    logger.info("Starting up application...")

    # Load translations
    init_translations()
    logger.info("Translations loaded")

    # Initialize database
    try:
        await init_database()
        logger.info("Database connection initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    # Initialize Redis
    try:
        await init_redis()
        logger.info("Redis connection initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Redis: {e}")
        raise

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down application...")

    # Close database connection
    try:
        await close_database()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")

    # Close Redis connection
    try:
        await close_redis()
        logger.info("Redis connection closed")
    except Exception as e:
        logger.error(f"Error closing Redis: {e}")

    logger.info("Application shutdown complete")
