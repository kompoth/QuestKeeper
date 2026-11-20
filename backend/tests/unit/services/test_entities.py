from datetime import UTC, datetime

import pytest

from app.domain.models import Article, Entity, Map, MapPin, PermissionLevel, World
from app.domain.repositories import Repositories
from app.services.access import (
    EntityNotFoundError,
    EntityNotInTrashError,
    IdCollisionError,
    PermissionDeniedError,
    WorldNotFoundError,
)
from app.services.entities import (
    clear_article,
    clear_map,
    create_entity,
    delete_entity,
    get_entity,
    list_entities,
    list_trash,
    purge_entity,
    rename_entity,
    restore_entity,
    restore_entity_branch,
    set_article,
    set_map,
)
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

WORLD_ID = "w1"
OWNER_ID = "owner"
USER_ID = "user"
ENTITY_ID = "e1"
PARENT_ID = "e0"


def make_repos(
    *, entity=None, other_entities=(), world=None, ancestor_ids=(), grants=None, collide_next_creates=0
) -> Repositories:
    entities_by_id = {other.id: other for other in other_entities}
    if entity:
        entities_by_id[entity.id] = entity
    entities = FakeEntityRepository(
        entities_by_id=entities_by_id,
        ancestor_ids_by_entity={entity.id: list(ancestor_ids)} if entity else {},
        collide_next_creates=collide_next_creates,
    )
    worlds = FakeWorldRepository(worlds_by_id={world.id: world} if world else {})
    permissions = FakeEntityPermissionRepository(grants_by_user={USER_ID: grants} if grants is not None else {})
    return Repositories(
        users=FakeUserRepository(),
        worlds=worlds,
        entities=entities,
        permissions=permissions,
        invites=FakeWorldInviteRepository(),
        sessions=FakeSessionRepository(),
        password_resets=FakePasswordResetRepository(),
        registration_confirmations=FakeRegistrationConfirmationRepository(),
        runtime_settings=FakeRuntimeSettingsRepository(),
    )


async def test_list_entities_succeeds_for_world_owner():
    world = World(id=WORLD_ID, owner_id=USER_ID, name="World")
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity")
    repos = make_repos(entity=entity, world=world)

    result = await list_entities(repos, USER_ID, WORLD_ID)

    assert [found.id for found, _ in result] == [ENTITY_ID]


async def test_list_entities_succeeds_for_a_user_with_any_grant_in_the_world():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity")
    repos = make_repos(entity=entity, world=world, grants={ENTITY_ID: PermissionLevel.READ})

    result = await list_entities(repos, USER_ID, WORLD_ID)

    assert [found.id for found, _ in result] == [ENTITY_ID]


async def test_list_entities_reports_write_access_from_the_callers_grant():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity")
    repos = make_repos(entity=entity, world=world, grants={ENTITY_ID: PermissionLevel.WRITE})

    [(_, access)] = await list_entities(repos, USER_ID, WORLD_ID)

    assert access.read is True
    assert access.write is True


async def test_list_entities_excludes_entities_the_caller_cannot_read():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Readable")
    other_entity = Entity(id="e2", world_id=WORLD_ID, name="Unreadable")
    repos = make_repos(
        entity=entity, other_entities=[other_entity], world=world, grants={ENTITY_ID: PermissionLevel.READ}
    )

    result = await list_entities(repos, USER_ID, WORLD_ID)

    assert [found.id for found, _ in result] == [ENTITY_ID]


async def test_list_entities_raises_when_caller_has_no_grants_in_the_world():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world, grants={})

    with pytest.raises(PermissionDeniedError):
        await list_entities(repos, USER_ID, WORLD_ID)


async def test_list_entities_raises_when_world_not_found():
    repos = make_repos()

    with pytest.raises(WorldNotFoundError):
        await list_entities(repos, USER_ID, WORLD_ID)


async def test_get_entity_succeeds_with_read_access():
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity")
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(entity=entity, world=world, grants={ENTITY_ID: PermissionLevel.READ})

    found, access = await get_entity(repos, USER_ID, WORLD_ID, ENTITY_ID)

    assert found == entity
    assert access.read is True


async def test_get_entity_raises_without_read_access():
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity")
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(entity=entity, world=world, grants={})

    with pytest.raises(PermissionDeniedError):
        await get_entity(repos, USER_ID, WORLD_ID, ENTITY_ID)


async def test_get_entity_raises_when_not_found():
    repos = make_repos()

    with pytest.raises(EntityNotFoundError):
        await get_entity(repos, USER_ID, WORLD_ID, ENTITY_ID)


async def test_create_entity_as_root_succeeds_for_world_owner():
    world = World(id=WORLD_ID, owner_id=USER_ID, name="World")
    repos = make_repos(world=world)

    entity_id = await create_entity(repos, USER_ID, WORLD_ID, None, "New Entity")

    entity = await repos.entities.get(WORLD_ID, entity_id)
    assert entity is not None
    assert entity.name == "New Entity"
    assert entity.created_by == USER_ID


async def test_create_entity_as_root_raises_when_caller_is_not_owner():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world)

    with pytest.raises(PermissionDeniedError):
        await create_entity(repos, USER_ID, WORLD_ID, None, "New Entity")


async def test_create_entity_as_root_raises_when_world_not_found():
    repos = make_repos()

    with pytest.raises(WorldNotFoundError):
        await create_entity(repos, USER_ID, WORLD_ID, None, "New Entity")


async def test_create_entity_generates_a_short_id():
    world = World(id=WORLD_ID, owner_id=USER_ID, name="World")
    repos = make_repos(world=world)

    entity_id = await create_entity(repos, USER_ID, WORLD_ID, None, "New Entity")

    assert len(entity_id) == 12


async def test_create_entity_retries_once_on_id_collision():
    world = World(id=WORLD_ID, owner_id=USER_ID, name="World")
    repos = make_repos(world=world, collide_next_creates=1)

    entity_id = await create_entity(repos, USER_ID, WORLD_ID, None, "New Entity")

    entity = await repos.entities.get(WORLD_ID, entity_id)
    assert entity is not None


async def test_create_entity_raises_after_a_second_id_collision():
    world = World(id=WORLD_ID, owner_id=USER_ID, name="World")
    repos = make_repos(world=world, collide_next_creates=2)

    with pytest.raises(IdCollisionError):
        await create_entity(repos, USER_ID, WORLD_ID, None, "New Entity")


async def test_create_entity_as_child_succeeds_with_write_grant_on_parent():
    parent = Entity(id=PARENT_ID, world_id=WORLD_ID, name="Parent")
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(entity=parent, world=world, grants={PARENT_ID: PermissionLevel.WRITE})

    entity_id = await create_entity(repos, USER_ID, WORLD_ID, PARENT_ID, "Child")

    entity = await repos.entities.get(WORLD_ID, entity_id)
    assert entity is not None


async def test_create_entity_as_child_raises_without_write_on_parent():
    parent = Entity(id=PARENT_ID, world_id=WORLD_ID, name="Parent")
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(entity=parent, world=world, grants={PARENT_ID: PermissionLevel.READ})

    with pytest.raises(PermissionDeniedError):
        await create_entity(repos, USER_ID, WORLD_ID, PARENT_ID, "Child")


async def test_create_entity_as_child_raises_when_parent_not_found():
    repos = make_repos()

    with pytest.raises(EntityNotFoundError):
        await create_entity(repos, USER_ID, WORLD_ID, PARENT_ID, "Child")


async def test_rename_entity_succeeds_with_write_access():
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity")
    world = World(id=WORLD_ID, owner_id=USER_ID, name="World")
    repos = make_repos(entity=entity, world=world)

    await rename_entity(repos, USER_ID, WORLD_ID, ENTITY_ID, "Renamed")

    renamed = await repos.entities.get(WORLD_ID, ENTITY_ID)
    assert renamed is not None
    assert renamed.name == "Renamed"


async def test_rename_entity_raises_without_write_access():
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity")
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(entity=entity, world=world, grants={ENTITY_ID: PermissionLevel.READ})

    with pytest.raises(PermissionDeniedError):
        await rename_entity(repos, USER_ID, WORLD_ID, ENTITY_ID, "Renamed")


async def test_delete_entity_succeeds_when_caller_can_delete():
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity", parent=PARENT_ID)
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(
        entity=entity,
        world=world,
        ancestor_ids=[PARENT_ID],
        grants={ENTITY_ID: PermissionLevel.WRITE, PARENT_ID: PermissionLevel.WRITE},
    )

    await delete_entity(repos, USER_ID, WORLD_ID, ENTITY_ID)

    assert await repos.entities.get(WORLD_ID, ENTITY_ID) is None


async def test_delete_entity_raises_when_caller_cannot_delete():
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity", parent=PARENT_ID)
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(entity=entity, world=world, ancestor_ids=[PARENT_ID], grants={ENTITY_ID: PermissionLevel.WRITE})

    with pytest.raises(PermissionDeniedError):
        await delete_entity(repos, USER_ID, WORLD_ID, ENTITY_ID)


async def test_set_article_raises_without_write_access():
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity")
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(entity=entity, world=world, grants={})

    with pytest.raises(PermissionDeniedError):
        await set_article(repos, USER_ID, WORLD_ID, ENTITY_ID, "# Hello")


async def test_set_article_persists_markdown_with_write_access():
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity")
    world = World(id=WORLD_ID, owner_id=USER_ID, name="World")
    repos = make_repos(entity=entity, world=world)

    await set_article(repos, USER_ID, WORLD_ID, ENTITY_ID, "# Hello")

    updated = await repos.entities.get(WORLD_ID, ENTITY_ID)
    assert updated is not None
    assert updated.article == Article(markdown="# Hello")


async def test_clear_article_removes_article_with_write_access():
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity", article=Article(markdown="# Hello"))
    world = World(id=WORLD_ID, owner_id=USER_ID, name="World")
    repos = make_repos(entity=entity, world=world)

    await clear_article(repos, USER_ID, WORLD_ID, ENTITY_ID)

    updated = await repos.entities.get(WORLD_ID, ENTITY_ID)
    assert updated is not None
    assert updated.article is None


async def test_set_map_persists_map_with_write_access():
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity")
    world = World(id=WORLD_ID, owner_id=USER_ID, name="World")
    repos = make_repos(entity=entity, world=world)
    map_ = Map(pic="map.png", pins={(1.0, 2.0): MapPin(entity_id="pinned", x=1, y=2)})

    await set_map(repos, USER_ID, WORLD_ID, ENTITY_ID, map_)

    updated = await repos.entities.get(WORLD_ID, ENTITY_ID)
    assert updated is not None
    assert updated.map == map_


async def test_clear_map_removes_map_with_write_access():
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity", map=Map(pic="map.png"))
    world = World(id=WORLD_ID, owner_id=USER_ID, name="World")
    repos = make_repos(entity=entity, world=world)

    await clear_map(repos, USER_ID, WORLD_ID, ENTITY_ID)

    updated = await repos.entities.get(WORLD_ID, ENTITY_ID)
    assert updated is not None
    assert updated.map is None


async def test_list_trash_returns_only_deleted_entities_the_caller_can_read():
    now = datetime.now(UTC)
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    readable = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Readable", deleted_at=now)
    unreadable = Entity(id="e2", world_id=WORLD_ID, name="Unreadable", deleted_at=now)
    repos = make_repos(
        entity=readable, other_entities=[unreadable], world=world, grants={ENTITY_ID: PermissionLevel.READ}
    )

    result = await list_trash(repos, USER_ID, WORLD_ID)

    assert [found.id for found, _ in result] == [ENTITY_ID]


async def test_restore_entity_also_restores_still_trashed_ancestors():
    now = datetime.now(UTC)
    parent = Entity(id=PARENT_ID, world_id=WORLD_ID, name="Parent", deleted_at=now)
    child = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Child", parent=PARENT_ID, deleted_at=now)
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(
        entity=child,
        other_entities=[parent],
        world=world,
        ancestor_ids=[PARENT_ID],
        grants={ENTITY_ID: PermissionLevel.WRITE, PARENT_ID: PermissionLevel.WRITE},
    )

    await restore_entity(repos, USER_ID, WORLD_ID, ENTITY_ID)

    restored_child = await repos.entities.get(WORLD_ID, ENTITY_ID)
    restored_parent = await repos.entities.get(WORLD_ID, PARENT_ID)
    assert restored_child is not None
    assert restored_parent is not None


async def test_restore_entity_stops_at_first_alive_ancestor():
    now = datetime.now(UTC)
    grandparent = Entity(id="gp", world_id=WORLD_ID, name="Grandparent", updated_by="someone-else")
    parent = Entity(id=PARENT_ID, world_id=WORLD_ID, name="Parent", parent="gp", deleted_at=now)
    child = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Child", parent=PARENT_ID, deleted_at=now)
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(
        entity=child,
        other_entities=[parent, grandparent],
        world=world,
        ancestor_ids=[PARENT_ID, "gp"],
        grants={ENTITY_ID: PermissionLevel.WRITE, PARENT_ID: PermissionLevel.WRITE},
    )

    await restore_entity(repos, USER_ID, WORLD_ID, ENTITY_ID)

    restored_grandparent = await repos.entities.get(WORLD_ID, "gp")
    assert restored_grandparent is not None
    assert restored_grandparent.updated_by == "someone-else"  # already alive - the cascade stopped here


async def test_restore_entity_branch_restores_descendants_and_ancestors():
    now = datetime.now(UTC)
    parent = Entity(id=PARENT_ID, world_id=WORLD_ID, name="Parent", deleted_at=now)
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity", parent=PARENT_ID, deleted_at=now)
    child = Entity(id="child1", world_id=WORLD_ID, name="Child", parent=ENTITY_ID, deleted_at=now)
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(
        entity=entity,
        other_entities=[parent, child],
        world=world,
        ancestor_ids=[PARENT_ID],
        grants={ENTITY_ID: PermissionLevel.WRITE, PARENT_ID: PermissionLevel.WRITE},
    )

    await restore_entity_branch(repos, USER_ID, WORLD_ID, ENTITY_ID)

    assert (await repos.entities.get(WORLD_ID, ENTITY_ID)) is not None
    assert (await repos.entities.get(WORLD_ID, PARENT_ID)) is not None
    assert (await repos.entities.get(WORLD_ID, "child1")) is not None


async def test_restore_entity_raises_when_not_in_trash():
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity", parent=PARENT_ID)
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(
        entity=entity,
        world=world,
        ancestor_ids=[PARENT_ID],
        grants={ENTITY_ID: PermissionLevel.WRITE, PARENT_ID: PermissionLevel.WRITE},
    )

    with pytest.raises(EntityNotInTrashError):
        await restore_entity(repos, USER_ID, WORLD_ID, ENTITY_ID)


async def test_restore_entity_raises_without_delete_access():
    now = datetime.now(UTC)
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity", parent=PARENT_ID, deleted_at=now)
    parent = Entity(id=PARENT_ID, world_id=WORLD_ID, name="Parent")
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(
        entity=entity,
        other_entities=[parent],
        world=world,
        ancestor_ids=[PARENT_ID],
        grants={ENTITY_ID: PermissionLevel.WRITE},
    )

    with pytest.raises(PermissionDeniedError):
        await restore_entity(repos, USER_ID, WORLD_ID, ENTITY_ID)


async def test_purge_entity_removes_entity_and_descendants():
    now = datetime.now(UTC)
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity", parent=PARENT_ID, deleted_at=now)
    parent = Entity(id=PARENT_ID, world_id=WORLD_ID, name="Parent")
    child = Entity(id="child1", world_id=WORLD_ID, name="Child", parent=ENTITY_ID, deleted_at=now)
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(
        entity=entity,
        other_entities=[parent, child],
        world=world,
        ancestor_ids=[PARENT_ID],
        grants={ENTITY_ID: PermissionLevel.WRITE, PARENT_ID: PermissionLevel.WRITE},
    )

    await purge_entity(repos, USER_ID, WORLD_ID, ENTITY_ID)

    assert (await repos.entities.get(WORLD_ID, ENTITY_ID)) is None
    assert (await repos.entities.get(WORLD_ID, "child1")) is None
    assert (await repos.entities.get(WORLD_ID, PARENT_ID)) is not None
