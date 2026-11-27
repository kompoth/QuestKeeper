import os

# Settings is one object validated as a whole, so any field read (here just database_url)
# requires every required field to be present - fill in the ones this suite never exercises.
os.environ.setdefault("FRONTEND_ORIGIN", "http://localhost:5173")
os.environ.setdefault("SMTP_HOST", "localhost")
os.environ.setdefault("SMTP_FROM_ADDRESS", "test@example.com")

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession, create_async_engine

from app.adapters.db.orm import Base
from app.config import get_settings


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def db_engine():
    """Created once for the whole integration run, reused by every test, torn down at the end."""
    engine = create_async_engine(get_settings().database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def db_connection(db_engine: AsyncEngine):
    """A connection with an outer transaction that's always rolled back, isolating each test.

    `connection.begin()` used as a context manager commits on clean exit, not rolls back - the
    transaction must be driven manually to guarantee the rollback runs regardless of test outcome.
    """
    async with db_engine.connect() as connection:
        transaction = await connection.begin()
        try:
            yield connection
        finally:
            await transaction.rollback()


@pytest_asyncio.fixture(loop_scope="session")
async def db_session(db_connection: AsyncConnection):
    async with AsyncSession(
        bind=db_connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    ) as session:
        yield session
