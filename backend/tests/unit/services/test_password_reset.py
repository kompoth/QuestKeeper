from datetime import UTC, datetime, timedelta

import pytest

from app.domain.models import PasswordReset, Session, User, UserRole
from app.domain.repositories import Repositories
from app.domain.security import verify_password
from app.services.access import PasswordResetTokenNotFoundError, UserNotFoundError
from app.services.password_reset import request_password_reset, request_password_reset_for_user, reset_password
from tests.unit.services.fakes import (
    FakeEntityPermissionRepository,
    FakeEntityRepository,
    FakeMailer,
    FakePasswordResetRepository,
    FakeRegistrationConfirmationRepository,
    FakeRuntimeSettingsRepository,
    FakeSessionRepository,
    FakeUserRepository,
    FakeWorldInviteRepository,
    FakeWorldRepository,
)

USER_ID = "u1"
EMAIL = "user@example.com"
OLD_PASSWORD = "old password"  # noqa: S105
NEW_PASSWORD = "new password"  # noqa: S105
FRONTEND_ORIGIN = "http://localhost:5173"


def make_user() -> User:
    return User(id=USER_ID, name="User", email=EMAIL, hashed_password="hashed-old", role=UserRole.MEMBER)


def make_repos(*, users=None, sessions=None, password_resets=None) -> Repositories:
    return Repositories(
        users=FakeUserRepository(users_by_id=users or {}),
        worlds=FakeWorldRepository(),
        entities=FakeEntityRepository(),
        permissions=FakeEntityPermissionRepository(),
        invites=FakeWorldInviteRepository(),
        sessions=sessions or FakeSessionRepository(),
        password_resets=password_resets or FakePasswordResetRepository(),
        registration_confirmations=FakeRegistrationConfirmationRepository(),
        runtime_settings=FakeRuntimeSettingsRepository(),
    )


async def test_request_password_reset_sends_mail_for_existing_user():
    password_resets = FakePasswordResetRepository()
    repos = make_repos(users={USER_ID: make_user()}, password_resets=password_resets)
    mailer = FakeMailer()

    await request_password_reset(repos, mailer, EMAIL, frontend_origin=FRONTEND_ORIGIN)

    assert len(password_resets.resets_by_user_id) == 1
    reset = next(iter(password_resets.resets_by_user_id.values()))
    assert reset.user_id == USER_ID
    assert len(mailer.password_resets) == 1
    to_email, reset_url = mailer.password_resets[0]
    assert to_email == EMAIL
    assert reset.token in reset_url


async def test_request_password_reset_noops_silently_for_unknown_email():
    password_resets = FakePasswordResetRepository()
    repos = make_repos(password_resets=password_resets)
    mailer = FakeMailer()

    await request_password_reset(repos, mailer, "missing@example.com", frontend_origin=FRONTEND_ORIGIN)

    assert password_resets.resets_by_user_id == {}
    assert mailer.password_resets == []


async def test_request_password_reset_for_user_sends_mail_for_known_user_id():
    password_resets = FakePasswordResetRepository()
    repos = make_repos(users={USER_ID: make_user()}, password_resets=password_resets)
    mailer = FakeMailer()

    await request_password_reset_for_user(repos, mailer, USER_ID, frontend_origin=FRONTEND_ORIGIN)

    assert len(password_resets.resets_by_user_id) == 1
    assert password_resets.resets_by_user_id[USER_ID].user_id == USER_ID
    assert len(mailer.password_resets) == 1
    assert mailer.password_resets[0][0] == EMAIL


async def test_request_password_reset_for_user_raises_for_unknown_user_id():
    repos = make_repos()
    mailer = FakeMailer()

    with pytest.raises(UserNotFoundError):
        await request_password_reset_for_user(repos, mailer, "missing", frontend_origin=FRONTEND_ORIGIN)


async def test_second_request_invalidates_the_first_outstanding_token():
    password_resets = FakePasswordResetRepository()
    repos = make_repos(users={USER_ID: make_user()}, password_resets=password_resets)
    mailer = FakeMailer()

    await request_password_reset(repos, mailer, EMAIL, frontend_origin=FRONTEND_ORIGIN)
    first_token = mailer.password_resets[0][1].split("token=")[1]

    await request_password_reset_for_user(repos, mailer, USER_ID, frontend_origin=FRONTEND_ORIGIN)

    assert await password_resets.get(first_token) is None


async def test_reset_password_updates_hash_deletes_token_and_revokes_other_sessions():
    users = FakeUserRepository(users_by_id={USER_ID: make_user()})
    sessions = FakeSessionRepository(
        sessions_by_token={
            "keep-mine": Session(token="keep-mine", user_id="other-user", expires_at=_far_future()),
            "revoke-me": Session(token="revoke-me", user_id=USER_ID, expires_at=_far_future()),
        }
    )
    reset = PasswordReset(token="reset-tok", user_id=USER_ID, expires_at=_far_future())
    password_resets = FakePasswordResetRepository(resets_by_user_id={USER_ID: reset})
    repos = make_repos(users=users.users_by_id, sessions=sessions, password_resets=password_resets)

    await reset_password(repos, "reset-tok", NEW_PASSWORD)

    updated_user = users.users_by_id[USER_ID]
    assert verify_password(NEW_PASSWORD, updated_user.hashed_password)
    assert await password_resets.get("reset-tok") is None
    assert "revoke-me" not in sessions.sessions_by_token
    assert "keep-mine" in sessions.sessions_by_token


async def test_reset_password_raises_for_unknown_or_expired_token():
    repos = make_repos()

    with pytest.raises(PasswordResetTokenNotFoundError):
        await reset_password(repos, "missing-token", NEW_PASSWORD)


def _far_future():
    return datetime.now(UTC) + timedelta(days=1)
