"""Orchestrates repository lookups with the pure decisions in `permissions`."""

from app.domain import permissions
from app.domain.models import EntityId, UserId, WorldId
from app.domain.permissions import EntityAccess
from app.domain.repositories import Repositories
from app.services.errors import EntityNotFoundError

FULL_ACCESS = EntityAccess(read=True, write=True, can_delete=True)


async def get_entity_access(
    repos: Repositories, user_id: UserId, world_id: WorldId, entity_id: EntityId, *, include_deleted: bool = False
) -> EntityAccess:
    """A user's access to an entity: fetched from the repos, decided by `permissions`.

    `include_deleted` lets trash flows (read, restore, purge) resolve access for a soft-deleted entity;
    every other caller leaves it unset, so a soft-deleted entity still raises EntityNotFoundError there.
    """
    entity = await repos.entities.get(world_id, entity_id, include_deleted=include_deleted)
    if entity is None:
        raise EntityNotFoundError(entity_id)

    world = await repos.worlds.get(world_id)
    if world is not None and permissions.is_owner(world, user_id):
        return FULL_ACCESS

    ancestor_ids = await repos.entities.get_ancestor_ids(world_id, entity_id)
    grants = await repos.permissions.get_grants(world_id, user_id)
    return permissions.resolve_access(entity_id, ancestor_ids, grants)
