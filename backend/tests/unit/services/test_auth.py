from datetime import UTC, datetime, timedelta

import pytest

from app.domain.models import Session, User, UserRole
from app.domain.repositories import Repositories
from app.domain.security import hash_password
from app.services.auth import InvalidCredentialsError, InvalidSessionError, get_current_user, login, logout
from tests.unit.services.fakes import (
    FakeEntityRepository,
    FakeInviteRepository,
    FakePasswordResetRepository,
    FakePendingRegistrationRepository,
    FakePermissionRepository,
    FakeSessionRepository,
    FakeUserRepository,
    FakeWorldRepository,
)

USER_ID = "u1"
EMAIL = "user@example.com"
PASSWORD = "correct horse battery staple"  # noqa: S105


def make_repos(*, users=None, sessions=None) -> Repositories:
    return Repositories(
        users=FakeUserRepository(users_by_id=users or {}),
        worlds=FakeWorldRepository(),
        entities=FakeEntityRepository(),
        permissions=FakePermissionRepository(),
        invites=FakeInviteRepository(),
        sessions=sessions or FakeSessionRepository(),
        password_resets=FakePasswordResetRepository(),
        pending_registrations=FakePendingRegistrationRepository(),
    )


def make_user() -> User:
    return User(id=USER_ID, name="User", email=EMAIL, hashed_password=hash_password(PASSWORD), role=UserRole.MEMBER)


async def test_login_succeeds_and_persists_a_session_for_the_correct_password():
    repos = make_repos(users={USER_ID: make_user()})

    session = await login(repos, EMAIL, PASSWORD)

    assert session.user_id == USER_ID
    assert await repos.sessions.get(session.token) == session


async def test_login_raises_when_email_is_unknown():
    repos = make_repos()

    with pytest.raises(InvalidCredentialsError):
        await login(repos, EMAIL, PASSWORD)


async def test_login_raises_when_password_is_wrong():
    repos = make_repos(users={USER_ID: make_user()})

    with pytest.raises(InvalidCredentialsError):
        await login(repos, EMAIL, "wrong password")


async def test_logout_deletes_the_session():
    sessions = FakeSessionRepository()
    repos = make_repos(users={USER_ID: make_user()}, sessions=sessions)
    session = await login(repos, EMAIL, PASSWORD)

    await logout(repos, session.token)

    assert await sessions.get(session.token) is None


async def test_get_current_user_returns_the_session_owner():
    user = make_user()
    session = Session(token="tok", user_id=USER_ID, expires_at=datetime.now(UTC) + timedelta(days=1))
    repos = make_repos(users={USER_ID: user}, sessions=FakeSessionRepository(sessions_by_token={"tok": session}))

    found = await get_current_user(repos, "tok")

    assert found == user


async def test_get_current_user_raises_for_an_unknown_token():
    repos = make_repos()

    with pytest.raises(InvalidSessionError):
        await get_current_user(repos, "missing")


async def test_get_current_user_raises_for_an_expired_session():
    session = Session(token="tok", user_id=USER_ID, expires_at=datetime.now(UTC) - timedelta(seconds=1))
    repos = make_repos(users={USER_ID: make_user()}, sessions=FakeSessionRepository(sessions_by_token={"tok": session}))

    with pytest.raises(InvalidSessionError):
        await get_current_user(repos, "tok")
