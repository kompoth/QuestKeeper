from datetime import UTC, datetime, timedelta

import pytest

from app.domain.models import User, UserRole, WorldInvite
from app.domain.repositories import Repositories
from app.services.access import EmailAlreadyRegisteredError, InviteTokenNotFoundError
from app.services.signup import confirm_invite_signup
from tests.unit.services.fakes import (
    FakeEntityPermissionRepository,
    FakeEntityRepository,
    FakePasswordResetRepository,
    FakePendingRegistrationRepository,
    FakeSessionRepository,
    FakeUserRepository,
    FakeWorldInviteRepository,
    FakeWorldRepository,
)

EMAIL = "new@example.com"
PASSWORD = "correct horse battery staple"  # noqa: S105


def make_repos(*, invites=None, users=None) -> Repositories:
    return Repositories(
        users=FakeUserRepository(users_by_id=users or {}),
        worlds=FakeWorldRepository(),
        entities=FakeEntityRepository(),
        permissions=FakeEntityPermissionRepository(),
        invites=invites if invites is not None else FakeWorldInviteRepository(),
        sessions=FakeSessionRepository(),
        password_resets=FakePasswordResetRepository(),
        pending_registrations=FakePendingRegistrationRepository(),
    )


def make_invite(invite_id: str, world_id: str, *, token: str | None = None, email: str = EMAIL) -> WorldInvite:
    return WorldInvite(
        id=invite_id,
        world_id=world_id,
        invitee_id=None,
        invitee_email=email,
        entity_id="e1",
        level="read",
        confirmation_token=token,
        token_expires_at=datetime.now(UTC) + timedelta(days=7) if token else None,
    )


async def test_confirm_invite_signup_creates_user_accepts_invite_and_logs_in():
    token = "tok"  # noqa: S105
    targeted_invite = make_invite("i1", "w1", token=token)
    other_pending_invite = make_invite("i2", "w2")
    invites = FakeWorldInviteRepository(invites=[targeted_invite, other_pending_invite])
    repos = make_repos(invites=invites)

    result = await confirm_invite_signup(repos, token, "New User", PASSWORD)

    assert result.user.email == EMAIL
    assert result.session.user_id == result.user.id

    # FakeWorldInviteRepository.accept() appends rather than mutating in place (matching the real SQL
    # adapter's semantics would require a DB-backed test); take the last i1 entry, which is the one
    # accept_invite() just passed to accept().
    invites_by_id = {invite.id: invite for invite in invites.invites}
    assert invites_by_id["i1"].invitee_id == result.user.id
    # Generalized backfill: the OTHER pending invite for this email also gets linked, not just i1's.
    assert invites_by_id["i2"].invitee_id == result.user.id


async def test_confirm_invite_signup_raises_when_token_unknown_or_expired():
    repos = make_repos()

    with pytest.raises(InviteTokenNotFoundError):
        await confirm_invite_signup(repos, "missing-token", "New User", PASSWORD)


async def test_confirm_invite_signup_raises_when_email_already_registered():
    token = "tok"  # noqa: S105
    invite = make_invite("i1", "w1", token=token)
    existing_user = User(id="existing", name="Existing", email=EMAIL, hashed_password="x", role=UserRole.MEMBER)
    users = FakeUserRepository(users_by_id={"existing": existing_user})
    repos = make_repos(invites=FakeWorldInviteRepository(invites=[invite]), users=users.users_by_id)

    with pytest.raises(EmailAlreadyRegisteredError):
        await confirm_invite_signup(repos, token, "New User", PASSWORD)

    assert users.users_by_id == {"existing": existing_user}
