import os

# FRONTEND_ORIGIN/SMTP_HOST/SMTP_FROM_ADDRESS defaults come from the parent conftest.py.
os.environ.setdefault("COOKIE_SECURE", "false")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from app.adapters.db.orm import UserRow
from app.api.dependencies import get_db_session, get_mailer
from app.domain.models import UserRole
from app.domain.security import hash_password
from app.main import app
from tests.unit.services.fakes import FakeMailer

EMAIL = "user@example.com"
PASSWORD = "correct horse battery staple"  # noqa: S105


@pytest.fixture
def mailer() -> FakeMailer:
    return FakeMailer()


def csrf_headers(async_client) -> dict[str, str]:
    return {"X-CSRF-Token": async_client.cookies["csrf_token"]}


async def login(async_client, db_session, *, user_id: str = "owner", email: str = EMAIL) -> None:
    """Creates a MEMBER user with the shared PASSWORD and logs them in via the real /auth/login route."""
    db_session.add(
        UserRow(id=user_id, name="User", email=email, hashed_password=hash_password(PASSWORD), role=UserRole.MEMBER)
    )
    await db_session.commit()
    await async_client.post("/auth/login", json={"email": email, "password": PASSWORD})


@pytest_asyncio.fixture(loop_scope="session")
async def async_client(db_connection: AsyncConnection, mailer: FakeMailer):
    """A client wired to the test DB, giving each request its own fresh session on the same connection.

    Binding every request's session to the test's own `db_connection` (same one `db_session` uses)
    keeps everything inside the single outer transaction that gets rolled back at teardown - a session
    bound to a different connection from the engine's pool would be a separate real transaction and
    its writes could actually persist against MySQL.
    """

    async def override_get_db_session():
        async with AsyncSession(
            bind=db_connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
        ) as session:
            yield session
            await session.commit()

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_mailer] = lambda: mailer
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.clear()
