import os

os.environ.setdefault("FRONTEND_ORIGIN", "http://localhost:5173")
os.environ.setdefault("COOKIE_SECURE", "false")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.api.dependencies import get_db_session, get_mailer
from app.main import app
from tests.services.fakes import FakeMailer


@pytest.fixture
def mailer() -> FakeMailer:
    return FakeMailer()


@pytest_asyncio.fixture
async def async_client(db_engine: AsyncEngine, mailer: FakeMailer):
    """A client wired to the test DB, giving each request its own fresh session on the same connection.

    Reusing one `AsyncSession` across requests (like the real app's db_session fixture does within a
    test) breaks SQLAlchemy's async lazy-loading once requests span different asyncio tasks; a fresh
    session per request, sharing the engine's single `StaticPool` connection, avoids that.
    """
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db_session():
        async with session_factory() as session:
            yield session
            await session.commit()

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_mailer] = lambda: mailer
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.clear()
