import pytest

from app.domain.models import User, UserRole
from app.services.avatar import clear_avatar, request_avatar_upload, set_avatar
from app.services.errors import MediaTooLargeError, UnsupportedMediaTypeError, UserNotFoundError
from tests.unit.services.fakes import FakeMediaStorage, FakeUserRepository, make_repos

USER_ID = "u1"


def make_user(*, avatar: str | None = None) -> User:
    return User(
        id=USER_ID, name="User", email="user@test.com", hashed_password="x", role=UserRole.MEMBER, avatar=avatar
    )


async def test_request_avatar_upload_mints_a_global_scoped_key():
    storage = FakeMediaStorage()

    file_id, policy = await request_avatar_upload(
        storage, content_type="image/png", size=12, max_bytes=1024, ttl_seconds=60
    )

    assert file_id
    assert storage.created_policies == [f"global/{file_id}"]
    assert policy.url


async def test_request_avatar_upload_rejects_unsupported_content_type():
    with pytest.raises(UnsupportedMediaTypeError):
        await request_avatar_upload(
            FakeMediaStorage(), content_type="image/svg+xml", size=12, max_bytes=1024, ttl_seconds=60
        )


async def test_request_avatar_upload_rejects_oversized_declared_size():
    with pytest.raises(MediaTooLargeError):
        await request_avatar_upload(
            FakeMediaStorage(), content_type="image/png", size=2048, max_bytes=1024, ttl_seconds=60
        )


async def test_set_avatar_sets_the_callers_own_avatar():
    repos = make_repos(users=FakeUserRepository(users_by_id={USER_ID: make_user()}))

    updated = await set_avatar(repos, FakeMediaStorage(), USER_ID, "new-file")

    assert updated.avatar == "/media/new-file"
    stored = await repos.users.get_by_id(USER_ID)
    assert stored is not None
    assert stored.avatar == "/media/new-file"


async def test_set_avatar_deletes_the_old_avatar_file_when_replaced():
    repos = make_repos(users=FakeUserRepository(users_by_id={USER_ID: make_user(avatar="/media/old-file")}))
    storage = FakeMediaStorage()

    await set_avatar(repos, storage, USER_ID, "new-file")

    assert storage.deleted_prefixes == ["global/old-file"]


async def test_set_avatar_does_not_delete_an_avatar_that_is_not_our_own_reference_shape():
    repos = make_repos(
        users=FakeUserRepository(users_by_id={USER_ID: make_user(avatar="https://placeholder.test/avatar.png")})
    )
    storage = FakeMediaStorage()

    await set_avatar(repos, storage, USER_ID, "new-file")

    assert storage.deleted_prefixes == []


async def test_set_avatar_raises_when_user_not_found():
    repos = make_repos()

    with pytest.raises(UserNotFoundError):
        await set_avatar(repos, FakeMediaStorage(), USER_ID, "new-file")


async def test_clear_avatar_removes_the_avatar_and_deletes_its_file():
    repos = make_repos(users=FakeUserRepository(users_by_id={USER_ID: make_user(avatar="/media/old-file")}))
    storage = FakeMediaStorage()

    updated = await clear_avatar(repos, storage, USER_ID)

    assert updated.avatar is None
    stored = await repos.users.get_by_id(USER_ID)
    assert stored is not None
    assert stored.avatar is None
    assert storage.deleted_prefixes == ["global/old-file"]


async def test_clear_avatar_raises_when_user_not_found():
    repos = make_repos()

    with pytest.raises(UserNotFoundError):
        await clear_avatar(repos, FakeMediaStorage(), USER_ID)
