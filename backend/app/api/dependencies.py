"""Shared FastAPI dependencies: DB session, repositories, current user, CSRF."""

from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.db.session import create_engine, create_session_factory
from app.composition import build_mailer, build_media_storage, build_repositories
from app.config import Settings, get_settings
from app.domain.mail import Mailer
from app.domain.media import MediaStorage
from app.domain.models import User, UserRole
from app.domain.repositories import Repositories
from app.services import auth

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"


@lru_cache(maxsize=1)
def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    return create_session_factory(create_engine(get_settings().database_url))


async def get_db_session() -> AsyncIterator[AsyncSession]:
    session_factory = _get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_repositories(session: Annotated[AsyncSession, Depends(get_db_session, scope="function")]) -> Repositories:
    return build_repositories(session)


def get_mailer() -> Mailer:
    return build_mailer()


def get_media_storage() -> MediaStorage:
    return build_media_storage()


Repos = Annotated[Repositories, Depends(get_repositories)]
MailerDep = Annotated[Mailer, Depends(get_mailer)]
MediaStorageDep = Annotated[MediaStorage, Depends(get_media_storage)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionToken = Annotated[str, Depends(auth.cookie_scheme)]


async def current_user(token: SessionToken, repos: Repos) -> User:
    return await auth.get_current_user(repos, token)


CurrentUser = Annotated[User, Depends(current_user)]


def require_csrf(request: Request) -> None:
    cookie_value = request.cookies.get(CSRF_COOKIE_NAME)
    header_value = request.headers.get(CSRF_HEADER_NAME)
    if not cookie_value or cookie_value != header_value:
        raise HTTPException(status_code=403, detail="Missing or invalid CSRF token")


async def require_registration_enabled(repos: Repos) -> None:
    settings = await repos.runtime_settings.get()
    if not settings.registration_enabled:
        raise HTTPException(status_code=403, detail="Registration is currently disabled")


async def require_password_reset_enabled(repos: Repos) -> None:
    settings = await repos.runtime_settings.get()
    if not settings.password_reset_enabled:
        raise HTTPException(status_code=403, detail="Password reset is currently disabled")


def require_admin(user: CurrentUser) -> None:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin role required")
