import pytest

from app.domain.models import World
from app.domain.repositories import Repositories
from app.services.access import PermissionDeniedError, WorldNotFoundError
from app.services.worlds import create_world, update_world
from tests.services.fakes import (
    FakeEntityRepository,
    FakeInviteRepository,
    FakePermissionRepository,
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
    )


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
