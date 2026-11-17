"""Orchestrates entity mutations with the access checks from `services.access`."""

from uuid import uuid4

from app.domain import permissions
from app.domain.models import Article, EntityId, Map, UserId, WorldId
from app.domain.repositories import Repositories
from app.services.access import PermissionDeniedError, WorldNotFoundError, get_entity_access


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

    entity_id = str(uuid4())
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
