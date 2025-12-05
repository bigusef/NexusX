# Configuration

This document describes all configuration options available in Nexus.

## Environment Variables

All configuration is done through environment variables. Copy `.env.example` to `.env` and customize as needed.

### Core Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENVIRONMENT` | No | `development` | Application environment: `development`, `testing`, `staging`, or `production` |
| `ALLOWED_ORIGINS` | No | `*` | CORS allowed origins (comma-separated or `*` for all) |

### Database Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string in format: `postgresql+asyncpg://user:password@host:port/database` |

**Example:**
```
DATABASE_URL=postgresql+asyncpg://nexus:nexus@postgres:5432/nexus
```

### Redis Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | Yes | - | Redis connection string in format: `redis://host:port/db` |

**Example:**
```
REDIS_URL=redis://redis:6379/0
```

### JWT Authentication

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_SECRET_KEY` | Yes | - | Secret key for signing JWT tokens. Generate with: `openssl rand -hex 32` |
| `JWT_ACCESS_EXPIRATION` | No | `15m` | Access token expiration time |
| `JWT_REFRESH_EXPIRATION` | No | `7d` | Refresh token expiration time |

**Time Format:**
- `s` - seconds (e.g., `30s`)
- `m` - minutes (e.g., `15m`)
- `h` - hours (e.g., `2h`)
- `d` - days (e.g., `7d`)

**Example:**
```
JWT_SECRET_KEY=your-super-secret-key-generated-with-openssl
JWT_ACCESS_EXPIRATION=15m
JWT_REFRESH_EXPIRATION=7d
```

## Environment Modes

The `ENVIRONMENT` variable controls application behavior:

| Environment | Debug Mode | API Docs | Description |
|-------------|------------|----------|-------------|
| `development` | Enabled | Enabled | Local development |
| `testing` | Enabled | Enabled | Running tests |
| `staging` | Enabled | Enabled | Pre-production testing |
| `production` | Disabled | Disabled | Production deployment |

### Debug Mode Effects

When debug mode is enabled:
- Detailed error messages are returned
- SQL queries may be logged
- Additional development endpoints are available

### API Documentation

Swagger UI and ReDoc are available at `/docs` and `/redoc` respectively when not in production mode.

## Configuration Classes

Configuration is managed through Pydantic Settings classes in `src/core/config.py`:

```python
class Settings(BaseSettings):
    environment: Environment
    allowed_origins: list[str]
    database: DatabaseSettings
    redis: RedisSettings
    jwt: JWTSettings
```

### Accessing Configuration

```python
from src.core import settings

# Access settings
db_url = settings.database_url
jwt_secret = settings.jwt.secret_key
is_debug = settings.debug
```

## Docker Configuration

When running with Docker Compose, environment variables are loaded from `.env.example` by default:

```yaml
# docker-compose.yml
services:
  api:
    env_file: .env.example
```

For production, create a `.env` file with production values and update the compose file:

```yaml
services:
  api:
    env_file: .env
```

## Example Configuration

### Development (.env.example)

```bash
# Environment
ENVIRONMENT=development
ALLOWED_ORIGINS=*

# Database (Docker internal network)
DATABASE_URL=postgresql+asyncpg://nexus:nexus@postgres:5432/nexus

# Redis (Docker internal network)
REDIS_URL=redis://redis:6379/0

# JWT (use a real secret in production!)
JWT_SECRET_KEY=your-super-secret-key-change-in-production
JWT_ACCESS_EXPIRATION=15m
JWT_REFRESH_EXPIRATION=7d
```

### Production

```bash
# Environment
ENVIRONMENT=production
ALLOWED_ORIGINS=https://yourdomain.com,https://api.yourdomain.com

# Database (external or managed database)
DATABASE_URL=postgresql+asyncpg://user:strongpassword@db.example.com:5432/nexus_prod

# Redis (external or managed Redis)
REDIS_URL=redis://:password@redis.example.com:6379/0

# JWT (generate with: openssl rand -hex 32)
JWT_SECRET_KEY=a1b2c3d4e5f6...your-64-character-hex-string
JWT_ACCESS_EXPIRATION=15m
JWT_REFRESH_EXPIRATION=7d
```

## Security Considerations

1. **JWT Secret Key**: Always use a strong, randomly generated secret key in production. Generate one with:
   ```bash
   openssl rand -hex 32
   ```

2. **Database Credentials**: Use strong passwords and consider using managed database services with encrypted connections.

3. **CORS Origins**: In production, specify exact allowed origins instead of using `*`.

4. **Environment File**: Never commit `.env` files with production credentials to version control.

5. **Token Expiration**: Balance security and user experience when setting token expiration times. Shorter access tokens are more secure but require more frequent refreshes.
