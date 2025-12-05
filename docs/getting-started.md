# Getting Started

This guide walks you through setting up Nexus for local development.

## Prerequisites

- **Python 3.13+** - Required for the application
- **Docker & Docker Compose** - For running PostgreSQL, Redis, and the application
- **UV** - Modern Python package manager ([installation guide](https://github.com/astral-sh/uv))
- **Git** - Version control

## Installation

### Clone the Repository

```bash
git clone https://github.com/your-username/nexus.git
cd nexus
```

### Environment Configuration

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env if you need to customize settings
# For development, the defaults work out of the box
```

## Running with Docker (Recommended)

The easiest way to run Nexus is with Docker Compose:

```bash
# Start all services (API, worker, PostgreSQL, Redis)
docker compose up -d

# View logs
docker compose logs -f api

# Stop services
docker compose down
```

### Services Overview

| Service | Container | Port | Description |
|---------|-----------|------|-------------|
| api | nexus-api | 8000 | FastAPI application with hot reload |
| worker | nexus-worker | - | ARQ background job processor |
| postgres | nexus-postgres | 5432 | PostgreSQL database |
| redis | nexus-redis | 6379 | Redis for cache and job queue |

## Running Locally (Without Docker for API)

If you prefer to run the API locally while using Docker for infrastructure:

```bash
# Start only infrastructure services
docker compose up -d postgres redis

# Install Python dependencies
uv sync

# Run database migrations
uv run alembic upgrade head

# Start the API with hot reload
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## Database Migrations

Nexus uses Alembic for database migrations.

### Running Migrations

```bash
# Apply all pending migrations
docker compose exec api uv run alembic upgrade head

# Or locally
uv run alembic upgrade head
```

### Creating New Migrations

```bash
# Auto-generate migration from model changes
uv run alembic revision --autogenerate -m "description of changes"

# Review the generated migration in alembic/versions/
# Then apply it
uv run alembic upgrade head
```

### Rolling Back

```bash
# Downgrade by one revision
uv run alembic downgrade -1

# Downgrade to specific revision
uv run alembic downgrade <revision_id>
```

## Running Tests

Tests use PostgreSQL (same as production) and fakeredis for isolation.

```bash
# Run all tests
docker compose exec api uv run pytest

# Run with verbose output
docker compose exec api uv run pytest -v

# Run specific test category
docker compose exec api uv run pytest tests/unit/
docker compose exec api uv run pytest tests/integration/
docker compose exec api uv run pytest tests/api/

# Run with coverage report
docker compose exec api uv run pytest --cov=src --cov-report=html
```

## CLI Commands

Nexus includes a CLI for common tasks. The CLI is available as `nexus` when installed.

### Translation Management (i18n)

```bash
# Extract translatable strings from source code
nexus i18n extract

# Initialize catalog for a specific language
nexus i18n init --lang ar

# Initialize catalogs for all supported languages
nexus i18n init --all

# Update existing catalogs with new strings
nexus i18n update

# Compile .po files to .mo (required for runtime)
nexus i18n compile
```

### User Management (auth)

```bash
# Create a new user (interactive)
nexus auth create

# Create a staff user
nexus auth create --staff

# Lock a user account
nexus auth lock

# Unlock a user account
nexus auth unlock

# Generate JWT tokens for a user
nexus auth generate-token
```

## Verifying the Setup

### Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "environment": "development"
}
```

### API Documentation

When running in development mode, API documentation is available at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

Note: Documentation is disabled in production environment.

## Development Workflow

### Typical Development Cycle

1. **Start services**: `docker compose up -d`
2. **Make code changes**: The API auto-reloads on file changes
3. **Run tests**: `docker compose exec api uv run pytest`
4. **Create migrations** (if models changed): `uv run alembic revision --autogenerate -m "..."`
5. **Apply migrations**: `docker compose exec api uv run alembic upgrade head`
6. **Commit changes**: Follow conventional commit format

### Code Quality

Before committing, ensure code passes quality checks:

```bash
# Run linter
uv run ruff check

# Auto-fix issues
uv run ruff check --fix

# Format code
uv run ruff format

# Run pre-commit hooks
uv run pre-commit run --all-files
```

## Troubleshooting

### Database Connection Issues

If you see database connection errors:

1. Ensure PostgreSQL is running: `docker compose ps`
2. Check the DATABASE_URL in your `.env` file
3. Verify the database exists: `docker compose exec postgres psql -U nexus -d nexus -c '\l'`

### Redis Connection Issues

If Redis-related features fail:

1. Ensure Redis is running: `docker compose ps`
2. Check the REDIS_URL in your `.env` file
3. Test connection: `docker compose exec redis redis-cli ping`

### Migration Errors

If migrations fail:

1. Check if tables already exist from a previous setup
2. Review the alembic_version table: `docker compose exec postgres psql -U nexus -d nexus -c 'SELECT * FROM alembic_version'`
3. You may need to stamp the current version: `uv run alembic stamp head`

## Next Steps

- Read the [Architecture Guide](architecture.md) to understand the project structure
- Review [Configuration](configuration.md) for all available settings
