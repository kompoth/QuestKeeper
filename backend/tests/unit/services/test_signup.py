from datetime import UTC, datetime, timedelta

import pytest

from app.domain.models import User, UserRole, UserStatus, WorldInvite
from app.domain.repositories import Repositories
from app.services.access import EmailAlreadyRegisteredError, InviteTokenNotFoundError
from app.services.signup import confirm_invite_signup
from tests.unit.services.fakes import (
    FakeEntityPermissionRepository,
    FakeEntityRepository,
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


def make_repos(*, invites=None, users=None) -> Repositories:
    return Repositories(
        users=FakeUserRepository(users_by_id=users or {}),
        worlds=FakeWorldRepository(),
        entities=FakeEntityRepository(),
        permissions=FakeEntityPermissionRepository(),
        invites=invites if invites is not None else FakeWorldInviteRepository(),
        sessions=FakeSessionRepository(),
        password_resets=FakePasswordResetRepository(),
        registration_confirmations=FakeRegistrationConfirmationRepository(),
        runtime_settings=FakeRuntimeSettingsRepository(),
    )


def make_pending_user(user_id: str, *, email: str = EMAIL) -> User:
    return User(
        id=user_id, name=email, email=email, hashed_password="x", role=UserRole.MEMBER, status=UserStatus.PENDING
    )


def make_invite(invite_id: str, world_id: str, invitee_id: str, *, token: str | None = None) -> WorldInvite:
    return WorldInvite(
        id=invite_id,
        world_id=world_id,
        invitee_id=invitee_id,
        confirmation_token=token,
        token_expires_at=datetime.now(UTC) + timedelta(days=7) if token else None,
    )


async def test_confirm_invite_signup_claims_the_pending_user_accepts_invite_and_logs_in():
    token = "tok"  # noqa: S105
    targeted_invite = make_invite("i1", "w1", "u1", token=token)
    # Already resolved to the same placeholder at invite-creation time - no backfill needed.
    other_invite = make_invite("i2", "w2", "u1")
    invites = FakeWorldInviteRepository(invites=[targeted_invite, other_invite])
    repos = make_repos(invites=invites, users={"u1": make_pending_user("u1")})

    result = await confirm_invite_signup(repos, token, "New User", PASSWORD)

    assert result.user.id == "u1"
    assert result.user.email == EMAIL
    assert result.user.name == "New User"
    assert result.user.status == UserStatus.ACTIVE
    assert result.session.user_id == "u1"

    claimed = await repos.users.get_by_id("u1")
    assert claimed is not None
    assert claimed.status == UserStatus.ACTIVE
    assert claimed.name == "New User"

    invites_by_id = {invite.id: invite for invite in invites.invites}
    assert invites_by_id["i1"].invitee_id == "u1"
    assert invites_by_id["i2"].invitee_id == "u1"


async def test_confirm_invite_signup_raises_when_token_unknown_or_expired():
    repos = make_repos()

    with pytest.raises(InviteTokenNotFoundError):
        await confirm_invite_signup(repos, "missing-token", "New User", PASSWORD)


async def test_confirm_invite_signup_raises_when_user_already_active():
    token = "tok"  # noqa: S105
    active_user = User(id="u1", name="Existing", email=EMAIL, hashed_password="x", role=UserRole.MEMBER)
    invite = make_invite("i1", "w1", "u1", token=token)
    repos = make_repos(invites=FakeWorldInviteRepository(invites=[invite]), users={"u1": active_user})

    with pytest.raises(EmailAlreadyRegisteredError):
        await confirm_invite_signup(repos, token, "New User", PASSWORD)

    assert await repos.users.get_by_id("u1") == active_user
