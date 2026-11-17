import pytest

from app.domain.models import Entity, PermissionLevel, World
from app.domain.permissions import EntityAccess
from app.domain.repositories import Repositories
from app.services.access import FULL_ACCESS, EntityNotFoundError, get_entity_access
from tests.services.fakes import (
    FakeEntityRepository,
    FakeInviteRepository,
    FakePermissionRepository,
    FakeSessionRepository,
    FakeUserRepository,
    FakeWorldRepository,
)

WORLD_ID = "w1"
OWNER_ID = "owner"
USER_ID = "user"
ENTITY_ID = "e1"
PARENT_ID = "e0"


def make_repos(*, entity, world=None, ancestor_ids=(), grants=None) -> Repositories:
    entities = FakeEntityRepository(
        entities_by_id={entity.id: entity} if entity else {},
        ancestor_ids_by_entity={entity.id: list(ancestor_ids)} if entity else {},
    )
    worlds = FakeWorldRepository(worlds_by_id={world.id: world} if world else {})
    permissions = FakePermissionRepository(grants_by_user={USER_ID: grants} if grants is not None else {})
    return Repositories(
        users=FakeUserRepository(),
        worlds=worlds,
        entities=entities,
        permissions=permissions,
        invites=FakeInviteRepository(),
        sessions=FakeSessionRepository(),
    )


async def test_raises_when_entity_not_found():
    repos = make_repos(entity=None, world=World(id=WORLD_ID, owner_id=OWNER_ID, name="World"))

    with pytest.raises(EntityNotFoundError):
        await get_entity_access(repos, USER_ID, WORLD_ID, ENTITY_ID)


async def test_world_owner_gets_full_access_regardless_of_grants():
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity")
    world = World(id=WORLD_ID, owner_id=USER_ID, name="World")
    repos = make_repos(entity=entity, world=world, grants={})

    access = await get_entity_access(repos, USER_ID, WORLD_ID, ENTITY_ID)

    assert access == FULL_ACCESS


async def test_missing_world_falls_through_to_grant_based_resolution():
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity")
    repos = make_repos(entity=entity, world=None, grants={ENTITY_ID: PermissionLevel.READ})

    access = await get_entity_access(repos, USER_ID, WORLD_ID, ENTITY_ID)

    assert access == EntityAccess(read=True, write=False, can_delete=False)


async def test_non_owner_with_no_grants_has_no_access():
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity")
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(entity=entity, world=world, grants={})

    access = await get_entity_access(repos, USER_ID, WORLD_ID, ENTITY_ID)

    assert access == EntityAccess(read=False, write=False, can_delete=False)


async def test_non_owner_with_read_grant_on_ancestor_can_read_but_not_write():
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity", parent=PARENT_ID)
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(entity=entity, world=world, ancestor_ids=[PARENT_ID], grants={PARENT_ID: PermissionLevel.READ})

    access = await get_entity_access(repos, USER_ID, WORLD_ID, ENTITY_ID)

    assert access.read is True
    assert access.write is False


async def test_non_owner_with_write_on_entity_and_parent_can_delete():
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity", parent=PARENT_ID)
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(
        entity=entity,
        world=world,
        ancestor_ids=[PARENT_ID],
        grants={ENTITY_ID: PermissionLevel.WRITE, PARENT_ID: PermissionLevel.WRITE},
    )

    access = await get_entity_access(repos, USER_ID, WORLD_ID, ENTITY_ID)

    assert access == EntityAccess(read=True, write=True, can_delete=True)
