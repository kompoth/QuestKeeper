from datetime import UTC, datetime, timedelta

import pytest

from app.domain.models import RegistrationConfirmation, User, UserRole, UserStatus
from app.domain.repositories import Repositories
from app.services.access import EmailAlreadyRegisteredError, RegistrationTokenNotFoundError
from app.services.registration import confirm_registration, request_registration
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

EMAIL = "new@example.com"
PASSWORD = "correct horse battery staple"  # noqa: S105
FRONTEND_ORIGIN = "http://localhost:5173"


def make_repos(*, users=None, registration_confirmations=None) -> Repositories:
    return Repositories(
        users=FakeUserRepository(users_by_id=users or {}),
        worlds=FakeWorldRepository(),
        entities=FakeEntityRepository(),
        permissions=FakeEntityPermissionRepository(),
        invites=FakeWorldInviteRepository(),
        sessions=FakeSessionRepository(),
        password_resets=FakePasswordResetRepository(),
        registration_confirmations=registration_confirmations or FakeRegistrationConfirmationRepository(),
        runtime_settings=FakeRuntimeSettingsRepository(),
    )


async def test_request_registration_sends_mail_and_persists_a_pending_user():
    confirmations = FakeRegistrationConfirmationRepository()
    repos = make_repos(registration_confirmations=confirmations)
    mailer = FakeMailer()

    await request_registration(repos, mailer, "New User", EMAIL, PASSWORD, frontend_origin=FRONTEND_ORIGIN)

    user = await repos.users.get_by_email(EMAIL)
    assert user is not None
    assert user.name == "New User"
    assert user.status == UserStatus.PENDING
    confirmation = confirmations.confirmations_by_user_id[user.id]
    assert len(mailer.registration_confirmations) == 1
    to_email, confirm_url = mailer.registration_confirmations[0]
    assert to_email == EMAIL
    assert confirmation.token in confirm_url


async def test_request_registration_rejects_an_already_active_email():
    existing = User(id="existing", name="Existing", email=EMAIL, hashed_password="x", role=UserRole.MEMBER)
    repos = make_repos(users={"existing": existing})
    mailer = FakeMailer()

    with pytest.raises(EmailAlreadyRegisteredError):
        await request_registration(repos, mailer, "New User", EMAIL, PASSWORD, frontend_origin=FRONTEND_ORIGIN)


async def test_re_requesting_for_an_already_pending_email_refreshes_it_in_place():
    confirmations = FakeRegistrationConfirmationRepository()
    repos = make_repos(registration_confirmations=confirmations)
    mailer = FakeMailer()

    await request_registration(repos, mailer, "First Name", EMAIL, PASSWORD, frontend_origin=FRONTEND_ORIGIN)
    first_user = await repos.users.get_by_email(EMAIL)
    assert first_user is not None
    first_token = confirmations.confirmations_by_user_id[first_user.id].token

    await request_registration(
        repos, mailer, "Second Name", EMAIL, "a different password", frontend_origin=FRONTEND_ORIGIN
    )

    second_user = await repos.users.get_by_email(EMAIL)
    assert second_user is not None
    assert second_user.id == first_user.id
    assert second_user.name == "Second Name"
    second_token = confirmations.confirmations_by_user_id[second_user.id].token
    assert second_token != first_token
    assert await confirmations.get(first_token) is None


async def test_confirm_registration_activates_the_user_and_logs_in():
    confirmations = FakeRegistrationConfirmationRepository()
    repos = make_repos(registration_confirmations=confirmations)
    mailer = FakeMailer()
    await request_registration(repos, mailer, "New User", EMAIL, PASSWORD, frontend_origin=FRONTEND_ORIGIN)
    pending = await repos.users.get_by_email(EMAIL)
    assert pending is not None
    token = confirmations.confirmations_by_user_id[pending.id].token

    result = await confirm_registration(repos, token)

    assert result.user.email == EMAIL
    assert result.user.name == "New User"
    assert result.user.status == UserStatus.ACTIVE
    assert result.session.user_id == result.user.id

    activated = await repos.users.get_by_email(EMAIL)
    assert activated is not None
    assert activated.status == UserStatus.ACTIVE
    assert await confirmations.get(token) is None


async def test_confirm_registration_raises_when_token_unknown():
    repos = make_repos()

    with pytest.raises(RegistrationTokenNotFoundError):
        await confirm_registration(repos, "missing-token")


async def test_confirm_registration_raises_when_token_expired():
    user = User(
        id="u1", name="Expired", email=EMAIL, hashed_password="x", role=UserRole.MEMBER, status=UserStatus.PENDING
    )
    expired = RegistrationConfirmation(
        token="expired-tok", user_id="u1", expires_at=datetime.now(UTC) - timedelta(seconds=1)
    )
    confirmations = FakeRegistrationConfirmationRepository(confirmations_by_user_id={"u1": expired})
    repos = make_repos(users={"u1": user}, registration_confirmations=confirmations)

    with pytest.raises(RegistrationTokenNotFoundError):
        await confirm_registration(repos, "expired-tok")
