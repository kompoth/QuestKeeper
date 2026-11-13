"""Engine and session-factory construction. Callers own the session's lifecycle."""

import os

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


def get_database_url() -> str:
    return os.environ["DATABASE_URL"]


def create_engine() -> AsyncEngine:
    return create_async_engine(get_database_url())


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
