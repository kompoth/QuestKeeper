import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.adapters.db import session as session_module


def test_get_database_url_reads_the_env_var(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    assert session_module.get_database_url() == "sqlite+aiosqlite:///:memory:"


def test_get_database_url_raises_key_error_when_unset(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(KeyError):
        session_module.get_database_url()


async def test_create_engine_and_session_factory_smoke(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    engine = session_module.create_engine()
    try:
        assert isinstance(engine, AsyncEngine)
        factory = session_module.create_session_factory(engine)
        assert isinstance(factory, async_sessionmaker)
    finally:
        await engine.dispose()
