import pytest

from app.domain.models import User, UserRole, UserStatus
from app.services.errors import (
    CannotBanSelfError,
    CannotChangeOwnRoleError,
    EmailAlreadyRegisteredError,
    UserNotFoundError,
)
from app.services.users import change_user_role, change_user_status, create_user, list_users
from tests.unit.services.fakes import FakeMailer, FakeUserRepository, make_repos

USER_A = User(id="u-a", name="A", email="a@example.com", hashed_password="x", role=UserRole.MEMBER)
USER_B = User(id="u-b", name="B", email="b@example.com", hashed_password="x", role=UserRole.MEMBER)
FRONTEND_ORIGIN = "http://localhost:3000"


async def test_list_users_returns_a_page_and_the_total_count():
    users = FakeUserRepository(users_by_id={USER_A.id: USER_A, USER_B.id: USER_B})
    repos = make_repos(users=users)

    page, total = await list_users(repos, offset=0, limit=1)

    assert total == 2
    assert [user.id for user in page] == [USER_A.id]


async def test_list_users_search_matches_name_case_insensitively():
    alice = User(id="u-alice", name="Alice Smith", email="alice@foo.com", hashed_password="x", role=UserRole.MEMBER)
    bob = User(id="u-bob", name="Bob Jones", email="bob@bar.com", hashed_password="x", role=UserRole.MEMBER)
    repos = make_repos(users=FakeUserRepository(users_by_id={alice.id: alice, bob.id: bob}))

    page, total = await list_users(repos, offset=0, limit=10, search="ALICE")

    assert total == 1
    assert [user.id for user in page] == [alice.id]


async def test_list_users_search_matches_email():
    alice = User(id="u-alice", name="Alice Smith", email="alice@foo.com", hashed_password="x", role=UserRole.MEMBER)
    bob = User(id="u-bob", name="Bob Jones", email="bob@bar.com", hashed_password="x", role=UserRole.MEMBER)
    repos = make_repos(users=FakeUserRepository(users_by_id={alice.id: alice, bob.id: bob}))

    page, total = await list_users(repos, offset=0, limit=10, search="bar.com")

    assert total == 1
    assert [user.id for user in page] == [bob.id]


async def test_change_user_role_updates_and_returns_the_user():
    users = FakeUserRepository(users_by_id={USER_A.id: USER_A, USER_B.id: USER_B})
    repos = make_repos(users=users)

    updated = await change_user_role(repos, USER_B.id, USER_A.id, UserRole.ADMIN)

    assert updated.role == UserRole.ADMIN
    persisted = await repos.users.get_by_id(USER_A.id)
    assert persisted is not None
    assert persisted.role == UserRole.ADMIN


async def test_change_user_role_raises_for_an_unknown_user():
    repos = make_repos(users=FakeUserRepository(users_by_id={USER_A.id: USER_A}))

    with pytest.raises(UserNotFoundError):
        await change_user_role(repos, USER_A.id, "missing", UserRole.ADMIN)


async def test_change_user_role_raises_when_changing_ones_own_role():
    users = FakeUserRepository(users_by_id={USER_A.id: USER_A})
    repos = make_repos(users=users)

    with pytest.raises(CannotChangeOwnRoleError):
        await change_user_role(repos, USER_A.id, USER_A.id, UserRole.ADMIN)

    persisted = await repos.users.get_by_id(USER_A.id)
    assert persisted is not None
    assert persisted.role == UserRole.MEMBER


async def test_create_user_creates_an_account_with_no_usable_password_and_emails_a_reset_link():
    repos = make_repos()
    mailer = FakeMailer()

    created = await create_user(
        repos, mailer, "New User", "new@example.com", UserRole.WARDEN, frontend_origin=FRONTEND_ORIGIN
    )

    assert created.role == UserRole.WARDEN
    persisted = await repos.users.get_by_email("new@example.com")
    assert persisted is not None
    assert persisted.id == created.id
    assert len(mailer.password_resets) == 1
    assert mailer.password_resets[0][0] == "new@example.com"


async def test_create_user_raises_for_a_taken_email():
    repos = make_repos(users=FakeUserRepository(users_by_id={USER_A.id: USER_A}))
    mailer = FakeMailer()

    with pytest.raises(EmailAlreadyRegisteredError):
        await create_user(repos, mailer, "Dupe", USER_A.email, UserRole.MEMBER, frontend_origin=FRONTEND_ORIGIN)


async def test_change_user_status_bans_and_returns_the_user():
    users = FakeUserRepository(users_by_id={USER_A.id: USER_A})
    repos = make_repos(users=users)

    updated = await change_user_status(repos, "admin", USER_A.id, UserStatus.BANNED)

    assert updated.status == UserStatus.BANNED
    persisted = await repos.users.get_by_id(USER_A.id)
    assert persisted is not None
    assert persisted.status == UserStatus.BANNED


async def test_change_user_status_raises_when_banning_oneself():
    users = FakeUserRepository(users_by_id={USER_A.id: USER_A})
    repos = make_repos(users=users)

    with pytest.raises(CannotBanSelfError):
        await change_user_status(repos, USER_A.id, USER_A.id, UserStatus.BANNED)

    persisted = await repos.users.get_by_id(USER_A.id)
    assert persisted is not None
    assert persisted.status == UserStatus.ACTIVE


async def test_change_user_status_allows_unbanning_oneself():
    banned_self = USER_A.model_copy(update={"status": UserStatus.BANNED})
    users = FakeUserRepository(users_by_id={banned_self.id: banned_self})
    repos = make_repos(users=users)

    updated = await change_user_status(repos, banned_self.id, banned_self.id, UserStatus.ACTIVE)

    assert updated.status == UserStatus.ACTIVE


async def test_change_user_status_raises_for_an_unknown_user():
    repos = make_repos()

    with pytest.raises(UserNotFoundError):
        await change_user_status(repos, "admin", "missing", UserStatus.BANNED)
