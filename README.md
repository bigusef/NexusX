# Nexus

A modern, production-ready FastAPI backend platform built with Clean Architecture principles and async-first design.

## Features

- **Async-First Design** - Built entirely on async/await patterns for maximum performance
- **Clean Architecture** - Domain-driven design with clear separation of concerns
- **JWT Authentication** - Secure token-based auth with refresh token rotation and device logout
- **Internationalization** - Multi-language support (AR, DE, EN, ES, FR, IT, RU) with Babel
- **Generic Repository** - Type-safe CRUD operations with pagination and filtering
- **Background Jobs** - ARQ-based task processing with Redis
- **Production Ready** - Docker multi-stage builds, health checks, and migrations

## Tech Stack

| Category | Technology |
|----------|------------|
| Language | Python 3.13+ |
| Framework | FastAPI |
| Database | PostgreSQL (asyncpg) |
| ORM | SQLAlchemy (async) |
| Migrations | Alembic |
| Cache/Broker | Redis |
| Background Jobs | ARQ |
| CLI | Typer |
| i18n | Babel |
| Package Manager | UV |
| Containerization | Docker & Docker Compose |

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git

### Run with Docker

```bash
# Clone the repository
git clone https://github.com/your-username/nexus.git
cd nexus

# Copy environment file
cp .env.example .env

# Start all services
docker compose up -d

# Run database migrations
docker compose exec api uv run alembic upgrade head

# Verify the API is running
curl http://localhost:8000/health
```

The API will be available at `http://localhost:8000`.

### Services

| Service | Port | Description |
|---------|------|-------------|
| api | 8000 | FastAPI application |
| worker | - | ARQ background worker |
| postgres | 5432 | PostgreSQL database |
| redis | 6379 | Redis cache & broker |

## Project Structure

```
nexus/
├── src/                    # Application source code
│   ├── main.py            # FastAPI entry point
│   ├── core/              # Infrastructure (config, db, redis, jwt, i18n)
│   ├── abstract/          # Base classes (Entity, Repository)
│   ├── domains/           # Business domains (auth, etc.)
│   ├── routers/           # API routes (admin, customer)
│   ├── exceptions/        # Custom exception hierarchy
│   └── utilities/         # Shared utilities and enums
├── cli/                   # CLI commands (Typer)
├── workers/               # Background job workers (ARQ)
├── alembic/               # Database migrations
├── locales/               # Translation files
├── tests/                 # Test suite
├── docker-compose.yml     # Container orchestration
└── Dockerfile             # Multi-stage Docker build
```

## Documentation

- [Getting Started](docs/getting-started.md) - Development setup and workflow
- [Architecture](docs/architecture.md) - Design patterns and project structure
- [Configuration](docs/configuration.md) - Environment variables reference

## Running Tests

```bash
# Run all tests
docker compose exec api uv run pytest

# Run with coverage
docker compose exec api uv run pytest --cov=src
```

## CLI Commands

```bash
# Translation management
nexus i18n extract      # Extract translatable strings
nexus i18n init --all   # Initialize all language catalogs
nexus i18n update       # Update catalogs with new strings
nexus i18n compile      # Compile translations

# User management
nexus auth create       # Create a new user
nexus auth lock         # Lock a user account
nexus auth unlock       # Unlock a user account
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
