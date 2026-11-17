import pytest

from app.domain.models import PermissionLevel, World
from app.domain.repositories import Repositories
from app.services.access import PermissionDeniedError, WorldNotFoundError
from app.services.worlds import create_world, get_world, list_worlds, update_world
from tests.services.fakes import (
    FakeEntityRepository,
    FakeInviteRepository,
    FakePasswordResetRepository,
    FakePendingRegistrationRepository,
    FakePermissionRepository,
    FakeSessionRepository,
    FakeUserRepository,
    FakeWorldRepository,
)

OWNER_ID = "owner"
OTHER_USER_ID = "other"
WORLD_ID = "w1"


def make_repos(*, world=None) -> Repositories:
    worlds = FakeWorldRepository(worlds_by_id={world.id: world} if world else {})
    return Repositories(
        users=FakeUserRepository(),
        worlds=worlds,
        entities=FakeEntityRepository(),
        permissions=FakePermissionRepository(),
        invites=FakeInviteRepository(),
        sessions=FakeSessionRepository(),
        password_resets=FakePasswordResetRepository(),
        pending_registrations=FakePendingRegistrationRepository(),
    )


async def test_list_worlds_returns_owned_and_granted_worlds_but_not_others():
    owned = World(id="w-owned", owner_id=OWNER_ID, name="Owned")
    granted = World(id="w-granted", owner_id=OTHER_USER_ID, name="Granted")
    other = World(id="w-other", owner_id=OTHER_USER_ID, name="Other")
    repos = Repositories(
        users=FakeUserRepository(),
        worlds=FakeWorldRepository(
            worlds_by_id={world.id: world for world in (owned, granted, other)},
            granted_world_ids_by_user={OWNER_ID: {"w-granted"}},
        ),
        entities=FakeEntityRepository(),
        permissions=FakePermissionRepository(),
        invites=FakeInviteRepository(),
        sessions=FakeSessionRepository(),
        password_resets=FakePasswordResetRepository(),
        pending_registrations=FakePendingRegistrationRepository(),
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
    repos = Repositories(
        users=FakeUserRepository(),
        worlds=FakeWorldRepository(worlds_by_id={WORLD_ID: world}),
        entities=FakeEntityRepository(),
        permissions=FakePermissionRepository(grants_by_user={OTHER_USER_ID: {"e1": PermissionLevel.READ}}),
        invites=FakeInviteRepository(),
        sessions=FakeSessionRepository(),
        password_resets=FakePasswordResetRepository(),
        pending_registrations=FakePendingRegistrationRepository(),
    )

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

    world = await repos.worlds.get(world_id)
    assert world is not None
    assert world.owner_id == OWNER_ID
    assert world.name == "My World"
    assert world.description == "A tale"


async def test_update_world_raises_when_world_not_found():
    repos = make_repos()
    patch = World(id=WORLD_ID, owner_id=OWNER_ID, name="New Name")

    with pytest.raises(WorldNotFoundError):
        await update_world(repos, OWNER_ID, patch)


async def test_update_world_raises_when_caller_is_not_owner():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world)
    patch = World(id=WORLD_ID, owner_id=OWNER_ID, name="New Name")

    with pytest.raises(PermissionDeniedError):
        await update_world(repos, OTHER_USER_ID, patch)


async def test_update_world_replaces_mutable_fields_for_the_owner():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World", description="Old")
    repos = make_repos(world=world)
    patch = World(id=WORLD_ID, owner_id=OWNER_ID, name="New Name", description="New", pic="pic.png")

    await update_world(repos, OWNER_ID, patch)

    updated = await repos.worlds.get(WORLD_ID)
    assert updated is not None
    assert updated.name == "New Name"
    assert updated.description == "New"
    assert updated.pic == "pic.png"
    assert updated.owner_id == OWNER_ID
