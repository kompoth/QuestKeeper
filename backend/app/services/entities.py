"""Orchestrates entity mutations with the access checks from `services.access`."""

import secrets
from collections.abc import Sequence

from app.domain import permissions
from app.domain.models import Article, Entity, EntityId, Map, UserId, WorldId
from app.domain.permissions import EntityAccess
from app.domain.repositories import Repositories
from app.services.access import (
    FULL_ACCESS,
    EntityNotFoundError,
    EntityNotInTrashError,
    IdCollisionError,
    PermissionDeniedError,
    WorldNotFoundError,
    get_entity_access,
)


async def list_entities(
    repos: Repositories, user_id: UserId, world_id: WorldId
) -> Sequence[tuple[Entity, EntityAccess]]:
    """Every entity the caller can read in the world, paired with their access to each; requires world membership."""
    world = await repos.worlds.get(world_id)
    if world is None:
        raise WorldNotFoundError(world_id)

    entities = await repos.entities.list_for_world(world_id)

    if permissions.is_owner(world, user_id):
        return [(entity, FULL_ACCESS) for entity in entities]

    grants = await repos.permissions.get_grants(world_id, user_id)
    if not grants:
        raise PermissionDeniedError(user_id, world_id)

    parent_by_id = {entity.id: entity.parent for entity in entities}

    def ancestor_ids(entity_id: EntityId) -> list[EntityId]:
        ids: list[EntityId] = []
        current = parent_by_id.get(entity_id)
        while current is not None:
            ids.append(current)
            current = parent_by_id.get(current)
        return ids

    results = [(entity, permissions.resolve_access(entity.id, ancestor_ids(entity.id), grants)) for entity in entities]
    return [(entity, access) for entity, access in results if access.read]


async def list_trash(repos: Repositories, user_id: UserId, world_id: WorldId) -> Sequence[tuple[Entity, EntityAccess]]:
    """Every soft-deleted entity the caller can read, paired with their access to each.

    Unlike `list_entities`, a trashed entity's ancestor chain can include alive entities (its parent,
    if only part of a once-larger subtree is still tombstoned) - so access is resolved per entity via
    `get_ancestor_ids`, not from an in-memory parent map built from this call's own (deleted-only) result.
    """
    world = await repos.worlds.get(world_id)
    if world is None:
        raise WorldNotFoundError(world_id)

    entities = await repos.entities.list_trash(world_id)

    if permissions.is_owner(world, user_id):
        return [(entity, FULL_ACCESS) for entity in entities]

    grants = await repos.permissions.get_grants(world_id, user_id)
    if not grants:
        raise PermissionDeniedError(user_id, world_id)

    results = []
    for entity in entities:
        ancestor_ids = await repos.entities.get_ancestor_ids(world_id, entity.id)
        results.append((entity, permissions.resolve_access(entity.id, ancestor_ids, grants)))
    return [(entity, access) for entity, access in results if access.read]


async def get_entity(
    repos: Repositories, user_id: UserId, world_id: WorldId, entity_id: EntityId
) -> tuple[Entity, EntityAccess]:
    """A single entity the caller can read - soft-deleted entities are included, so a trashed entity's
    page stays viewable (read-only) for anyone who could already read it."""
    access = await get_entity_access(repos, user_id, world_id, entity_id, include_deleted=True)
    if not access.read:
        raise PermissionDeniedError(user_id, entity_id)

    entity = await repos.entities.get(world_id, entity_id, include_deleted=True)
    if entity is None:
        raise RuntimeError(f"get_entity() found no entity right after get_entity_access() confirmed one: {entity_id}")
    return entity, access


async def create_entity(
    repos: Repositories, user_id: UserId, world_id: WorldId, parent_id: EntityId | None, name: str
) -> EntityId:
    """Creates a new entity.

    A root entity (no parent) requires world ownership; a child requires WRITE access on its
    intended parent.
    """
    if parent_id is None:
        world = await repos.worlds.get(world_id)
        if world is None:
            raise WorldNotFoundError(world_id)
        if not permissions.is_owner(world, user_id):
            raise PermissionDeniedError(user_id, world_id)
    else:
        access = await get_entity_access(repos, user_id, world_id, parent_id)
        if not access.write:
            raise PermissionDeniedError(user_id, parent_id)

    entity_id = secrets.token_urlsafe(9)
    try:
        await repos.entities.create(world_id, entity_id, name, parent_id, user_id)
    except IdCollisionError:
        # Vanishingly unlikely - regenerate and retry exactly once rather than fail the request.
        entity_id = secrets.token_urlsafe(9)
        await repos.entities.create(world_id, entity_id, name, parent_id, user_id)
    return entity_id


async def rename_entity(
    repos: Repositories, user_id: UserId, world_id: WorldId, entity_id: EntityId, name: str
) -> None:
    access = await get_entity_access(repos, user_id, world_id, entity_id)
    if not access.write:
        raise PermissionDeniedError(user_id, entity_id)

    await repos.entities.rename(entity_id, name, user_id)


async def delete_entity(repos: Repositories, user_id: UserId, world_id: WorldId, entity_id: EntityId) -> None:
    access = await get_entity_access(repos, user_id, world_id, entity_id)
    if not access.can_delete:
        raise PermissionDeniedError(user_id, entity_id)

    await repos.entities.delete(world_id, entity_id, user_id)


async def _require_trashed_entity_with_delete_access(
    repos: Repositories, user_id: UserId, world_id: WorldId, entity_id: EntityId
) -> Entity:
    """Shared guard for restore/restore-branch/purge: same access rule as delete_entity (WRITE on the
    parent), applied to a soft-deleted entity."""
    access = await get_entity_access(repos, user_id, world_id, entity_id, include_deleted=True)
    if not access.can_delete:
        raise PermissionDeniedError(user_id, entity_id)

    entity = await repos.entities.get(world_id, entity_id, include_deleted=True)
    if entity is None:
        raise EntityNotFoundError(entity_id)
    if entity.deleted_at is None:
        raise EntityNotInTrashError(entity_id)
    return entity


async def restore_entity(repos: Repositories, user_id: UserId, world_id: WorldId, entity_id: EntityId) -> None:
    """Restores only this entity; still-tombstoned descendants remain in trash."""
    await _require_trashed_entity_with_delete_access(repos, user_id, world_id, entity_id)
    await repos.entities.restore(world_id, entity_id, user_id)


async def restore_entity_branch(repos: Repositories, user_id: UserId, world_id: WorldId, entity_id: EntityId) -> None:
    """Restores this entity and every still-tombstoned entity in its descendant subtree."""
    await _require_trashed_entity_with_delete_access(repos, user_id, world_id, entity_id)
    await repos.entities.restore_branch(world_id, entity_id, user_id)


async def purge_entity(repos: Repositories, user_id: UserId, world_id: WorldId, entity_id: EntityId) -> None:
    """Permanently deletes this entity and its entire descendant subtree - irreversible."""
    await _require_trashed_entity_with_delete_access(repos, user_id, world_id, entity_id)
    await repos.entities.purge(world_id, entity_id)


async def set_article(
    repos: Repositories, user_id: UserId, world_id: WorldId, entity_id: EntityId, markdown: str
) -> None:
    access = await get_entity_access(repos, user_id, world_id, entity_id)
    if not access.write:
        raise PermissionDeniedError(user_id, entity_id)

    await repos.entities.set_article(entity_id, Article(markdown=markdown), user_id)


async def clear_article(repos: Repositories, user_id: UserId, world_id: WorldId, entity_id: EntityId) -> None:
    access = await get_entity_access(repos, user_id, world_id, entity_id)
    if not access.write:
        raise PermissionDeniedError(user_id, entity_id)

    await repos.entities.clear_article(entity_id, user_id)


async def set_map(repos: Repositories, user_id: UserId, world_id: WorldId, entity_id: EntityId, map_: Map) -> None:
    access = await get_entity_access(repos, user_id, world_id, entity_id)
    if not access.write:
        raise PermissionDeniedError(user_id, entity_id)

    await repos.entities.set_map(entity_id, map_, user_id)


async def clear_map(repos: Repositories, user_id: UserId, world_id: WorldId, entity_id: EntityId) -> None:
    access = await get_entity_access(repos, user_id, world_id, entity_id)
    if not access.write:
        raise PermissionDeniedError(user_id, entity_id)

    await repos.entities.clear_map(entity_id, user_id)
