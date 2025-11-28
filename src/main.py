"""Main FastAPI application entry point."""

from fastapi import FastAPI

from src.core.events import lifespan

app = FastAPI(
    title="Nexus Cortex",
    description="Nexus Cortex API's - Clean Architecture with FastAPI",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", include_in_schema=False)
async def health_check() -> dict[str, str]:
    """Health check endpoint for container orchestration."""
    return {"status": "healthy"}
