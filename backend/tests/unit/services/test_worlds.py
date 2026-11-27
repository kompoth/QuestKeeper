from datetime import UTC, datetime

import pytest

from app.domain.models import PermissionLevel, World, WorldInvite
from app.domain.repositories import Repositories
from app.services.errors import (
    IdCollisionError,
    PermissionDeniedError,
    UnsupportedMediaTypeError,
    WorldNotFoundError,
    WorldNotInTrashError,
)
from app.services.worlds import (
    create_world,
    delete_world,
    get_world,
    list_world_trash,
    list_worlds,
    purge_world,
    read_world_pic_redirect_url,
    request_world_pic_upload,
    restore_world,
    update_world,
)
from tests.unit.services.fakes import (
    FakeEntityPermissionRepository,
    FakeMediaStorage,
    FakeWorldInviteRepository,
    FakeWorldRepository,
)
from tests.unit.services.fakes import make_repos as _make_repos

OWNER_ID = "owner"
OTHER_USER_ID = "other"
WORLD_ID = "w1"


def make_repos(*, world=None, worlds=None, permissions=None, invites=None) -> Repositories:
    worlds = worlds or FakeWorldRepository(worlds_by_id={world.id: world} if world else {})
    return _make_repos(worlds=worlds, permissions=permissions, invites=invites)


async def test_list_worlds_returns_owned_and_granted_worlds_but_not_others():
    owned = World(id="w-owned", owner_id=OWNER_ID, name="Owned")
    granted = World(id="w-granted", owner_id=OTHER_USER_ID, name="Granted")
    other = World(id="w-other", owner_id=OTHER_USER_ID, name="Other")
    repos = make_repos(
        worlds=FakeWorldRepository(
            worlds_by_id={world.id: world for world in (owned, granted, other)},
            granted_world_ids_by_user={OWNER_ID: {"w-granted"}},
        )
    )

    result = await list_worlds(repos, OWNER_ID)

    assert {world.id for world in result} == {"w-owned", "w-granted"}


async def test_get_world_succeeds_for_owner():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world)

    found = await get_world(repos, OWNER_ID, WORLD_ID)

    assert found == world


async def test_get_world_succeeds_for_a_user_with_any_grant_in_the_world():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    permissions = FakeEntityPermissionRepository(grants_by_user={OTHER_USER_ID: {"e1": PermissionLevel.READ}})
    repos = make_repos(world=world, permissions=permissions)

    found = await get_world(repos, OTHER_USER_ID, WORLD_ID)

    assert found == world


async def test_get_world_succeeds_for_a_user_with_an_unaccepted_invite_and_no_grants():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    invite = WorldInvite(id="i1", world_id=WORLD_ID, invitee_id=OTHER_USER_ID, accepted=False)
    repos = make_repos(world=world, invites=FakeWorldInviteRepository(invites=[invite]))

    found = await get_world(repos, OTHER_USER_ID, WORLD_ID)

    assert found == world


async def test_get_world_raises_when_caller_has_no_grants_in_the_world():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world)

    with pytest.raises(PermissionDeniedError):
        await get_world(repos, OTHER_USER_ID, WORLD_ID)


async def test_get_world_raises_when_world_not_found():
    repos = make_repos()

    with pytest.raises(WorldNotFoundError):
        await get_world(repos, OWNER_ID, WORLD_ID)


async def test_create_world_persists_a_new_world_owned_by_the_caller():
    repos = make_repos()

    world_id = await create_world(repos, OWNER_ID, "My World", description="A tale")

    assert len(world_id) == 12
    world = await repos.worlds.get(world_id)
    assert world is not None
    assert world.owner_id == OWNER_ID
    assert world.name == "My World"
    assert world.description == "A tale"


async def test_create_world_retries_once_on_id_collision():
    worlds = FakeWorldRepository(collide_next_creates=1)
    repos = make_repos(worlds=worlds)

    world_id = await create_world(repos, OWNER_ID, "My World")

    assert world_id in worlds.worlds_by_id


async def test_create_world_raises_after_a_second_id_collision():
    repos = make_repos(worlds=FakeWorldRepository(collide_next_creates=2))

    with pytest.raises(IdCollisionError):
        await create_world(repos, OWNER_ID, "My World")


async def test_update_world_raises_when_world_not_found():
    repos = make_repos()

    with pytest.raises(WorldNotFoundError):
        await update_world(repos, FakeMediaStorage(), OWNER_ID, WORLD_ID, "New Name")


async def test_update_world_raises_when_caller_is_not_owner():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world)

    with pytest.raises(PermissionDeniedError):
        await update_world(repos, FakeMediaStorage(), OTHER_USER_ID, WORLD_ID, "New Name")


async def test_update_world_replaces_mutable_fields_for_the_owner():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World", description="Old")
    repos = make_repos(world=world)

    await update_world(repos, FakeMediaStorage(), OWNER_ID, WORLD_ID, "New Name", "New", "pic.png")

    updated = await repos.worlds.get(WORLD_ID)
    assert updated is not None
    assert updated.name == "New Name"
    assert updated.description == "New"
    assert updated.pic == "pic.png"
    assert updated.owner_id == OWNER_ID


async def test_update_world_deletes_the_old_pic_when_replaced():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World", pic="/api/worlds/w1/pic/old-file")
    repos = make_repos(world=world)
    storage = FakeMediaStorage()

    await update_world(repos, storage, OWNER_ID, WORLD_ID, "World", pic="/api/worlds/w1/pic/new-file")

    assert storage.deleted_prefixes == ["worlds/w1/pic/old-file"]


async def test_update_world_does_not_delete_when_pic_is_unchanged():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World", pic="/api/worlds/w1/pic/same-file")
    repos = make_repos(world=world)
    storage = FakeMediaStorage()

    await update_world(repos, storage, OWNER_ID, WORLD_ID, "World", pic="/api/worlds/w1/pic/same-file")

    assert storage.deleted_prefixes == []


async def test_update_world_does_not_delete_a_pic_that_is_not_our_own_reference_shape():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World", pic="https://placeholder.test/pic.png")
    repos = make_repos(world=world)
    storage = FakeMediaStorage()

    await update_world(repos, storage, OWNER_ID, WORLD_ID, "World", pic=None)

    assert storage.deleted_prefixes == []


async def test_delete_world_soft_deletes_it():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world)

    await delete_world(repos, OWNER_ID, WORLD_ID)

    assert await repos.worlds.get(WORLD_ID) is None
    trashed = await repos.worlds.get(WORLD_ID, include_deleted=True)
    assert trashed is not None
    assert trashed.deleted_at is not None


async def test_delete_world_raises_when_caller_is_not_owner():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world)

    with pytest.raises(PermissionDeniedError):
        await delete_world(repos, OTHER_USER_ID, WORLD_ID)


async def test_list_world_trash_returns_only_deleted_worlds_owned_by_caller():
    deleted_own = World(id="w-deleted", owner_id=OWNER_ID, name="Deleted", deleted_at=datetime.now(UTC))
    live_own = World(id="w-live", owner_id=OWNER_ID, name="Live")
    deleted_other = World(id="w-other", owner_id=OTHER_USER_ID, name="Other", deleted_at=datetime.now(UTC))
    worlds = FakeWorldRepository(worlds_by_id={world.id: world for world in (deleted_own, live_own, deleted_other)})
    repos = make_repos(worlds=worlds)

    result = await list_world_trash(repos, OWNER_ID)

    assert {world.id for world in result} == {"w-deleted"}


async def test_restore_world_succeeds_for_owner_of_a_trashed_world():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World", deleted_at=datetime.now(UTC))
    repos = make_repos(world=world)

    await restore_world(repos, OWNER_ID, WORLD_ID)

    restored = await repos.worlds.get(WORLD_ID)
    assert restored is not None
    assert restored.deleted_at is None


async def test_restore_world_raises_when_caller_is_not_owner():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World", deleted_at=datetime.now(UTC))
    repos = make_repos(world=world)

    with pytest.raises(PermissionDeniedError):
        await restore_world(repos, OTHER_USER_ID, WORLD_ID)


async def test_restore_world_raises_when_not_in_trash():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world)

    with pytest.raises(WorldNotInTrashError):
        await restore_world(repos, OWNER_ID, WORLD_ID)


async def test_purge_world_removes_a_trashed_world_owned_by_the_caller():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World", deleted_at=datetime.now(UTC))
    repos = make_repos(world=world)

    await purge_world(repos, FakeMediaStorage(), OWNER_ID, WORLD_ID)

    assert await repos.worlds.get(WORLD_ID, include_deleted=True) is None


async def test_purge_world_raises_when_caller_is_not_owner():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World", deleted_at=datetime.now(UTC))
    repos = make_repos(world=world)

    with pytest.raises(PermissionDeniedError):
        await purge_world(repos, FakeMediaStorage(), OTHER_USER_ID, WORLD_ID)


async def test_purge_world_raises_when_not_in_trash():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world)

    with pytest.raises(WorldNotInTrashError):
        await purge_world(repos, FakeMediaStorage(), OWNER_ID, WORLD_ID)


async def test_purge_world_sweeps_the_worlds_own_pic_prefix():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World", deleted_at=datetime.now(UTC))
    repos = make_repos(world=world)
    storage = FakeMediaStorage()

    await purge_world(repos, storage, OWNER_ID, WORLD_ID)

    assert f"worlds/{WORLD_ID}/pic/" in storage.deleted_prefixes


async def test_request_world_pic_upload_succeeds_for_owner():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world)
    storage = FakeMediaStorage()

    file_id, policy = await request_world_pic_upload(
        repos, storage, OWNER_ID, WORLD_ID, content_type="image/png", size=12, max_bytes=1024, ttl_seconds=60
    )

    assert file_id
    assert storage.created_policies == [f"worlds/{WORLD_ID}/pic/{file_id}"]
    assert policy.url


async def test_request_world_pic_upload_raises_when_caller_is_not_owner():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world)

    with pytest.raises(PermissionDeniedError):
        await request_world_pic_upload(
            repos,
            FakeMediaStorage(),
            OTHER_USER_ID,
            WORLD_ID,
            content_type="image/png",
            size=12,
            max_bytes=1024,
            ttl_seconds=60,
        )


async def test_request_world_pic_upload_raises_when_world_not_found():
    repos = make_repos()

    with pytest.raises(WorldNotFoundError):
        await request_world_pic_upload(
            repos,
            FakeMediaStorage(),
            OWNER_ID,
            WORLD_ID,
            content_type="image/png",
            size=12,
            max_bytes=1024,
            ttl_seconds=60,
        )


async def test_request_world_pic_upload_rejects_unsupported_content_type():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world)

    with pytest.raises(UnsupportedMediaTypeError):
        await request_world_pic_upload(
            repos,
            FakeMediaStorage(),
            OWNER_ID,
            WORLD_ID,
            content_type="image/svg+xml",
            size=12,
            max_bytes=1024,
            ttl_seconds=60,
        )


async def test_read_world_pic_redirect_url_succeeds_for_a_user_who_can_see_the_world():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world)
    storage = FakeMediaStorage()

    url = await read_world_pic_redirect_url(repos, storage, OWNER_ID, WORLD_ID, "f1", ttl_seconds=60)

    assert url == f"https://storage.test/worlds/{WORLD_ID}/pic/f1"


async def test_read_world_pic_redirect_url_raises_when_caller_cannot_see_the_world():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world)

    with pytest.raises(PermissionDeniedError):
        await read_world_pic_redirect_url(repos, FakeMediaStorage(), OTHER_USER_ID, WORLD_ID, "f1", ttl_seconds=60)
