from app.domain.models import User, UserRole, UserStatus
from app.domain.repositories import Repositories
from app.services.seed import ensure_seed_admin
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

EMAIL = "admin@example.com"
PASSWORD = "seed password"  # noqa: S105


def make_repos(*, users=None) -> Repositories:
    return Repositories(
        users=users or FakeUserRepository(),
        worlds=FakeWorldRepository(),
        entities=FakeEntityRepository(),
        permissions=FakeEntityPermissionRepository(),
        invites=FakeWorldInviteRepository(),
        sessions=FakeSessionRepository(),
        password_resets=FakePasswordResetRepository(),
        registration_confirmations=FakeRegistrationConfirmationRepository(),
        runtime_settings=FakeRuntimeSettingsRepository(),
    )


async def test_creates_an_admin_when_no_admin_exists_and_the_email_is_unknown():
    repos = make_repos()

    await ensure_seed_admin(repos, EMAIL, PASSWORD)

    created = await repos.users.get_by_email(EMAIL)
    assert created is not None
    assert created.role == UserRole.ADMIN


async def test_promotes_an_existing_user_with_the_matching_email_when_no_admin_exists():
    member = User(id="u1", name="Member", email=EMAIL, hashed_password="old-hash", role=UserRole.MEMBER)
    repos = make_repos(users=FakeUserRepository(users_by_id={member.id: member}))

    await ensure_seed_admin(repos, EMAIL, PASSWORD)

    promoted = await repos.users.get_by_id(member.id)
    assert promoted is not None
    assert promoted.role == UserRole.ADMIN
    assert promoted.hashed_password == "old-hash"  # noqa: S105


async def test_is_a_no_op_once_any_admin_already_exists():
    other_admin = User(id="u1", name="Other Admin", email="other@example.com", hashed_password="x", role=UserRole.ADMIN)
    repos = make_repos(users=FakeUserRepository(users_by_id={other_admin.id: other_admin}))

    await ensure_seed_admin(repos, EMAIL, PASSWORD)

    assert await repos.users.get_by_email(EMAIL) is None


async def test_is_idempotent_when_the_seed_account_is_already_admin():
    admin = User(id="u1", name="Admin", email=EMAIL, hashed_password="x", role=UserRole.ADMIN)
    repos = make_repos(users=FakeUserRepository(users_by_id={admin.id: admin}))

    await ensure_seed_admin(repos, EMAIL, PASSWORD)

    assert await repos.users.get_by_id(admin.id) == admin


async def test_creates_a_fresh_admin_when_the_only_existing_admin_is_banned():
    banned_admin = User(
        id="u1",
        name="Banned Admin",
        email="other@example.com",
        hashed_password="x",
        role=UserRole.ADMIN,
        status=UserStatus.BANNED,
    )
    repos = make_repos(users=FakeUserRepository(users_by_id={banned_admin.id: banned_admin}))

    await ensure_seed_admin(repos, EMAIL, PASSWORD)

    created = await repos.users.get_by_email(EMAIL)
    assert created is not None
    assert created.role == UserRole.ADMIN
    assert created.status == UserStatus.ACTIVE
