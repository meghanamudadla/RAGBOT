"""
Async SQLAlchemy session factory.

WHY ASYNC:
  FastAPI is fully async; using an async session avoids blocking the event
  loop on every DB call, enabling higher throughput with the same resources.
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

# asyncpg driver: postgresql+asyncpg://...
engine = create_async_engine(
    settings.POSTGRES_DSN,
    echo=settings.DEBUG,    # log SQL in debug mode
    pool_pre_ping=True,     # auto-reconnect on stale connections
    future=True,
)

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # keep objects accessible after commit
)


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields an async DB session."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
