"""Orchestrates entity mutations with the access checks from `services.access`."""

import secrets
from collections.abc import Sequence

from app.domain import permissions
from app.domain.models import Article, Entity, EntityId, Map, UserId, WorldId
from app.domain.permissions import EntityAccess
from app.domain.repositories import Repositories
from app.services.access import (
    FULL_ACCESS,
    IdCollisionError,
    PermissionDeniedError,
    WorldNotFoundError,
    get_entity_access,
)


async def list_entities(
    repos: Repositories, user_id: UserId, world_id: WorldId
) -> Sequence[tuple[Entity, EntityAccess]]:
    """Every entity in the world, paired with the caller's access to each; requires world membership."""
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

    return [(entity, permissions.resolve_access(entity.id, ancestor_ids(entity.id), grants)) for entity in entities]


async def get_entity(
    repos: Repositories, user_id: UserId, world_id: WorldId, entity_id: EntityId
) -> tuple[Entity, EntityAccess]:
    access = await get_entity_access(repos, user_id, world_id, entity_id)
    if not access.read:
        raise PermissionDeniedError(user_id, entity_id)

    entity = await repos.entities.get(world_id, entity_id)
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
