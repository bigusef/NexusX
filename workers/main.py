"""ARQ worker main entry point.

This module provides the ARQ worker configuration and task registry.
Run with: arq workers.main.WorkerSettings
"""

from arq.connections import RedisSettings

from src.core import settings


async def ping(ctx: dict) -> str:
    """Health check task for worker.

    A simple task that can be used to verify the worker is processing jobs.

    Args:
        ctx: Worker context dictionary.

    Returns:
        A simple pong response.
    """
    return "pong"


async def startup(ctx: dict) -> None:
    """Worker startup hook.

    Called when worker starts. Initialize any resources needed by tasks.

    Args:
        ctx: Worker context dictionary for sharing state between tasks.
    """
    pass


async def shutdown(ctx: dict) -> None:
    """Worker shutdown hook.

    Called when worker stops. Cleanup any resources.

    Args:
        ctx: Worker context dictionary.
    """
    pass


class WorkerSettings:
    """ARQ worker settings.

    Defines Redis connection, registered functions, and worker behavior.

    Attributes:
        redis_settings: Redis connection configuration.
        functions: List of async functions available as background tasks.
        cron_jobs: List of scheduled cron jobs.
        on_startup: Startup hook function.
        on_shutdown: Shutdown hook function.
        max_jobs: Maximum concurrent jobs per worker.
        job_timeout: Default timeout for jobs in seconds.
        keep_result: How long to keep job results in seconds.
        retry_jobs: Whether to retry failed jobs.
    """
    # Redis connection
    redis_settings = RedisSettings.from_dsn(settings.redis_url)

    # Task functions (can be called with arq)
    functions: list = [ping]

    # Cron jobs (scheduled tasks)
    cron_jobs: list = []

    on_startup = startup
    on_shutdown = shutdown

    max_jobs = 10  # Maximum concurrent jobs
    job_timeout = 300  # Job timeout in seconds (5 minutes)
    keep_result = 3600  # Keep job results for 1 hour
    retry_jobs = True
