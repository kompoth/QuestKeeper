"""Login, logout, and session-token resolution.

The token is an opaque, DB-backed string carried as an httpOnly cookie; CSRF needs a separate
double-submit check against an `X-CSRF-Token` header, not implemented here.
"""

import secrets
from datetime import UTC, datetime, timedelta

from fastapi.security import APIKeyCookie

from app.domain.models import Session, User, UserId, UserStatus
from app.domain.repositories import Repositories
from app.domain.security import verify_password

SESSION_TTL = timedelta(days=7)
SESSION_COOKIE_NAME = "session"

cookie_scheme = APIKeyCookie(name=SESSION_COOKIE_NAME)


class InvalidCredentialsError(Exception):
    pass


class InvalidSessionError(Exception):
    pass


class UserBannedError(Exception):
    pass


class UserPendingError(Exception):
    pass


async def create_session(repos: Repositories, user_id: UserId) -> Session:
    session = Session(token=secrets.token_urlsafe(32), user_id=user_id, expires_at=datetime.now(UTC) + SESSION_TTL)
    await repos.sessions.create(session)
    return session


async def login(repos: Repositories, email: str, password: str) -> Session:
    user = await repos.users.get_by_email(email)
    if user is None or not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError(email)

    if user.status == UserStatus.BANNED:
        raise UserBannedError("Your account has been banned")
    if user.status == UserStatus.PENDING:
        raise UserPendingError("Please confirm your email before logging in")

    return await create_session(repos, user.id)


async def logout(repos: Repositories, token: str) -> None:
    await repos.sessions.delete(token)


async def get_current_user(repos: Repositories, token: str) -> User:
    session = await repos.sessions.get(token)
    if session is None:
        raise InvalidSessionError(token)

    user = await repos.users.get_by_id(session.user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        # A non-active (banned or pending) user's existing session is treated as invalid, same as
        # logout - no need to distinguish the reason on every authenticated request.
        raise InvalidSessionError(token)
    return user
