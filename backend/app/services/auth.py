"""Login, logout, and session-token resolution.

The token is an opaque, DB-backed string carried as an httpOnly cookie; CSRF needs a separate
double-submit check against an `X-CSRF-Token` header, not implemented here.
"""

import secrets
from datetime import UTC, datetime, timedelta

from fastapi.security import APIKeyCookie

from app.domain.models import Session, User
from app.domain.repositories import Repositories
from app.domain.security import verify_password

SESSION_TTL = timedelta(days=7)
SESSION_COOKIE_NAME = "session"

cookie_scheme = APIKeyCookie(name=SESSION_COOKIE_NAME)


class InvalidCredentialsError(Exception):
    pass


class InvalidSessionError(Exception):
    pass


async def login(repos: Repositories, email: str, password: str) -> Session:
    user = await repos.users.get_by_email(email)
    if user is None or not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError(email)

    session = Session(token=secrets.token_urlsafe(32), user_id=user.id, expires_at=datetime.now(UTC) + SESSION_TTL)
    await repos.sessions.create(session)
    return session


async def logout(repos: Repositories, token: str) -> None:
    await repos.sessions.delete(token)


async def get_current_user(repos: Repositories, token: str) -> User:
    session = await repos.sessions.get(token)
    if session is None:
        raise InvalidSessionError(token)

    user = await repos.users.get_by_id(session.user_id)
    if user is None:
        raise InvalidSessionError(token)
    return user
