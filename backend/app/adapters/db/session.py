"""Engine and session-factory construction. Callers own the session's lifecycle."""

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


def create_engine(database_url: str) -> AsyncEngine:
    # Pool connections survive idle gaps longer than MariaDB's wait_timeout; without these,
    # a reused stale connection fails with "Lost connection to MySQL server" instead of reconnecting.
    return create_async_engine(database_url, pool_pre_ping=True, pool_recycle=3600)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
