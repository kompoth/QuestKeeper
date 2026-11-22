"""FastAPI app: CORS, exception handlers, routers, and startup seeding."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.db.session import create_engine, create_session_factory
from app.api.dependencies import CSRF_HEADER_NAME, enforce_csrf
from app.api.errors import register_exception_handlers
from app.api.routers.admin import router as admin_router
from app.api.routers.auth import router as auth_router
from app.api.routers.avatar import router as avatar_router
from app.api.routers.entities import router as entities_router
from app.api.routers.media import router as media_router
from app.api.routers.profile import router as profile_router
from app.api.routers.sharing import invites_router, permissions_router
from app.api.routers.worlds import router as worlds_router
from app.composition import build_repositories
from app.config import get_settings
from app.services.errors import EmailAlreadyRegisteredError
from app.services.seed import ensure_seed_admin


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    settings = get_settings()
    if settings.seed_admin_email or settings.seed_admin_password:
        if not (settings.seed_admin_email and settings.seed_admin_password):
            raise RuntimeError("SEED_ADMIN_EMAIL and SEED_ADMIN_PASSWORD must both be set, or neither.")

        engine = create_engine(settings.database_url)
        try:
            async with create_session_factory(engine)() as session:
                try:
                    await ensure_seed_admin(
                        build_repositories(session), settings.seed_admin_email, settings.seed_admin_password
                    )
                except EmailAlreadyRegisteredError:
                    # Another worker process won the race to seed this same account concurrently.
                    await session.rollback()
                else:
                    await session.commit()
        finally:
            await engine.dispose()

    yield


app = FastAPI(title="QuestKeeper", lifespan=lifespan, dependencies=[Depends(enforce_csrf)])

app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Content-Type", CSRF_HEADER_NAME],
)

register_exception_handlers(app)

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(avatar_router)
api_router.include_router(profile_router)
api_router.include_router(worlds_router)
api_router.include_router(entities_router)
api_router.include_router(media_router)
api_router.include_router(permissions_router)
api_router.include_router(invites_router)

app.include_router(api_router)
