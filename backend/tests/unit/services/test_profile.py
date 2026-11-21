import pytest

from app.domain.models import User, UserRole
from app.services.errors import UserNotFoundError
from app.services.profile import update_my_name
from tests.unit.services.fakes import FakeUserRepository, make_repos

USER_ID = "u1"


def make_user() -> User:
    return User(id=USER_ID, name="Old name", email="user@test.com", hashed_password="x", role=UserRole.MEMBER)


async def test_update_my_name_changes_the_callers_own_name():
    repos = make_repos(users=FakeUserRepository(users_by_id={USER_ID: make_user()}))

    updated = await update_my_name(repos, USER_ID, "New name")

    assert updated.name == "New name"
    stored = await repos.users.get_by_id(USER_ID)
    assert stored is not None
    assert stored.name == "New name"


async def test_update_my_name_raises_for_an_unknown_user():
    repos = make_repos(users=FakeUserRepository())

    with pytest.raises(UserNotFoundError):
        await update_my_name(repos, USER_ID, "New name")
