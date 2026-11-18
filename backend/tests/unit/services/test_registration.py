from datetime import UTC, datetime, timedelta

import pytest

from app.domain.models import PendingRegistration, User, UserRole, WorldInvite
from app.domain.repositories import Repositories
from app.services.access import EmailAlreadyRegisteredError, RegistrationTokenNotFoundError
from app.services.registration import confirm_registration, request_registration
from tests.unit.services.fakes import (
    FakeEntityPermissionRepository,
    FakeEntityRepository,
    FakeMailer,
    FakePasswordResetRepository,
    FakePendingRegistrationRepository,
    FakeSessionRepository,
    FakeUserRepository,
    FakeWorldInviteRepository,
    FakeWorldRepository,
)

EMAIL = "new@example.com"
PASSWORD = "correct horse battery staple"  # noqa: S105
FRONTEND_ORIGIN = "http://localhost:5173"


def make_repos(*, pending_registrations=None, invites=None, users=None) -> Repositories:
    return Repositories(
        users=FakeUserRepository(users_by_id=users or {}),
        worlds=FakeWorldRepository(),
        entities=FakeEntityRepository(),
        permissions=FakeEntityPermissionRepository(),
        invites=invites if invites is not None else FakeWorldInviteRepository(),
        sessions=FakeSessionRepository(),
        password_resets=FakePasswordResetRepository(),
        pending_registrations=pending_registrations or FakePendingRegistrationRepository(),
    )


def make_invite(invite_id: str, world_id: str, *, email: str = EMAIL) -> WorldInvite:
    return WorldInvite(
        id=invite_id, world_id=world_id, invitee_id=None, invitee_email=email, entity_id="e1", level="read"
    )


async def test_request_registration_sends_mail_and_persists_a_pending_row():
    pending_registrations = FakePendingRegistrationRepository()
    repos = make_repos(pending_registrations=pending_registrations)
    mailer = FakeMailer()

    await request_registration(repos, mailer, "New User", EMAIL, PASSWORD, frontend_origin=FRONTEND_ORIGIN)

    assert len(pending_registrations.pending_by_email) == 1
    pending = pending_registrations.pending_by_email[EMAIL]
    assert pending.name == "New User"
    assert len(mailer.registration_confirmations) == 1
    to_email, confirm_url = mailer.registration_confirmations[0]
    assert to_email == EMAIL
    assert pending.token in confirm_url


async def test_request_registration_rejects_an_already_registered_email():
    existing = User(id="existing", name="Existing", email=EMAIL, hashed_password="x", role=UserRole.MEMBER)
    repos = make_repos(users={"existing": existing})
    mailer = FakeMailer()

    with pytest.raises(EmailAlreadyRegisteredError):
        await request_registration(repos, mailer, "New User", EMAIL, PASSWORD, frontend_origin=FRONTEND_ORIGIN)


async def test_re_requesting_for_the_same_unconfirmed_email_replaces_the_pending_row():
    pending_registrations = FakePendingRegistrationRepository()
    repos = make_repos(pending_registrations=pending_registrations)
    mailer = FakeMailer()

    await request_registration(repos, mailer, "First Name", EMAIL, PASSWORD, frontend_origin=FRONTEND_ORIGIN)
    first_token = pending_registrations.pending_by_email[EMAIL].token

    await request_registration(
        repos, mailer, "Second Name", EMAIL, "a different password", frontend_origin=FRONTEND_ORIGIN
    )

    assert len(pending_registrations.pending_by_email) == 1
    second = pending_registrations.pending_by_email[EMAIL]
    assert second.name == "Second Name"
    assert second.token != first_token
    assert await pending_registrations.get_by_token(first_token) is None


async def test_confirm_registration_creates_user_deletes_pending_row_and_logs_in_and_backfills_invite():
    pending_registrations = FakePendingRegistrationRepository()
    repos = make_repos(pending_registrations=pending_registrations)
    mailer = FakeMailer()
    await request_registration(repos, mailer, "New User", EMAIL, PASSWORD, frontend_origin=FRONTEND_ORIGIN)
    token = pending_registrations.pending_by_email[EMAIL].token

    invite = make_invite("i1", "w1")
    invites = FakeWorldInviteRepository(invites=[invite])
    repos = make_repos(pending_registrations=pending_registrations, invites=invites)

    result = await confirm_registration(repos, token)

    assert result.user.email == EMAIL
    assert result.user.name == "New User"
    assert result.session.user_id == result.user.id
    assert await pending_registrations.get_by_token(token) is None

    invites_by_id = {invite.id: invite for invite in invites.invites}
    assert invites_by_id["i1"].invitee_id == result.user.id


async def test_confirm_registration_raises_when_token_unknown_or_expired():
    repos = make_repos()

    with pytest.raises(RegistrationTokenNotFoundError):
        await confirm_registration(repos, "missing-token")


async def test_confirm_registration_raises_when_token_expired():
    expired = FakePendingRegistrationRepository(
        pending_by_email={
            EMAIL: _expired_pending(),
        }
    )
    repos = make_repos(pending_registrations=expired)

    with pytest.raises(RegistrationTokenNotFoundError):
        await confirm_registration(repos, "expired-tok")


async def test_confirm_registration_raises_when_email_already_registered_in_the_meantime():
    pending_registrations = FakePendingRegistrationRepository()
    repos = make_repos(pending_registrations=pending_registrations)
    mailer = FakeMailer()
    await request_registration(repos, mailer, "New User", EMAIL, PASSWORD, frontend_origin=FRONTEND_ORIGIN)
    token = pending_registrations.pending_by_email[EMAIL].token

    existing = User(id="existing", name="Existing", email=EMAIL, hashed_password="x", role=UserRole.MEMBER)
    repos = make_repos(pending_registrations=pending_registrations, users={"existing": existing})

    with pytest.raises(EmailAlreadyRegisteredError):
        await confirm_registration(repos, token)


def _expired_pending() -> PendingRegistration:
    return PendingRegistration(
        token="expired-tok",
        name="Expired",
        email=EMAIL,
        hashed_password="x",
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
