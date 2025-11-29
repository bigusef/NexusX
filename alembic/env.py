"""Alembic environment configuration with async support and auto-discovery"""

import asyncio
import importlib
import logging
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import Entity and all entities for auto-discovery
from src.abstract.entity import Entity
from src.core import settings


# Setup logger for Alembic
logger = logging.getLogger("alembic")

# Auto-import all domain entities for Alembic auto-discovery
# This scans src/domains/ and imports all entities modules/packages automatically
domains_path = Path(__file__).parent.parent / "src" / "domains"
for domain_dir in domains_path.iterdir():
    if domain_dir.is_dir() and not domain_dir.name.startswith("_"):
        # Check for entities.py module or entities/ package
        entities_module = domain_dir / "entities.py"
        entities_package = domain_dir / "entities"

        if entities_module.exists() or (entities_package.exists() and (entities_package / "__init__.py").exists()):
            # Import the entities module to register models with Entity.metadata
            module_name = f"src.domains.{domain_dir.name}.entities"
            try:
                importlib.import_module(module_name)
            except ImportError as e:
                logger.warning(f"Could not import {module_name}: {e}")

# this is the Alembic Config object
config = context.config

# Override sqlalchemy.url with value from settings
config.set_main_option("sqlalchemy.url", settings.database_url)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support
target_metadata = Entity.metadata


def process_revision_directives(context, revision, directives):
    """
    Process revision directives to prevent empty migrations.

    If no changes are detected, this prevents Alembic from creating
    an empty migration file.
    """
    # Check if this is being run in autogenerate context
    if not directives or not hasattr(directives[0], "upgrade_ops"):
        return

    # Check if there are any actual changes
    if not directives[0].upgrade_ops.is_empty():
        logger.info("Changes detected - creating new revision file")
    else:
        logger.info("No changes detected - skipping creation of new revision file")
        directives[:] = []  # Clear directives to prevent empty migration


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        process_revision_directives=process_revision_directives,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with given connection"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        process_revision_directives=process_revision_directives,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode"""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode (with async support).

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
