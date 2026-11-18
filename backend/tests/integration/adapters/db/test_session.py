from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.adapters.db import session as session_module


async def test_create_engine_and_session_factory_smoke():
    engine = session_module.create_engine("mysql+aiomysql://user:pass@localhost/test")
    try:
        assert isinstance(engine, AsyncEngine)
        factory = session_module.create_session_factory(engine)
        assert isinstance(factory, async_sessionmaker)
    finally:
        await engine.dispose()
