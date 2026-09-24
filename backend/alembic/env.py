"""
Alembic env.py - configured for async SQLAlchemy with asyncpg.

WHY RUN_SYNC WRAPPER:
  Alembic's migration runner is synchronous, but our engine is async.
  run_sync wraps the Alembic migration calls in the async context so
  both can coexist.
"""
import asyncio
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# Import Base and all models so their tables are in target_metadata
from app.db.base import Base
import app.db.models  # noqa: F401  - side effect: registers all ORM models

from app.core.config import settings

# Alembic Config object
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.POSTGRES_DSN,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(settings.POSTGRES_DSN, future=True)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
