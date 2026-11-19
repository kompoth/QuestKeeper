"""Orchestrates repository lookups with the pure decisions in `permissions`."""

from app.domain import permissions
from app.domain.models import EntityId, UserId, WorldId
from app.domain.permissions import EntityAccess
from app.domain.repositories import Repositories

FULL_ACCESS = EntityAccess(read=True, write=True, can_delete=True)


class EntityNotFoundError(Exception):
    pass


class WorldNotFoundError(Exception):
    pass


class InviteNotFoundError(Exception):
    pass


class InviteTokenNotFoundError(Exception):
    pass


class EmailAlreadyRegisteredError(Exception):
    pass


class PasswordResetTokenNotFoundError(Exception):
    pass


class RegistrationTokenNotFoundError(Exception):
    pass


class UserNotFoundError(Exception):
    """Raised for an admin-targeted user_id lookup - never used on a public, email-based path."""


class PermissionDeniedError(Exception):
    pass


class CannotBanSelfError(Exception):
    pass


class CannotChangeOwnRoleError(Exception):
    pass


class InvalidStatusTransitionError(Exception):
    pass


class IdCollisionError(Exception):
    """A newly generated World/Entity id already exists - the caller should regenerate and retry."""


async def get_entity_access(
    repos: Repositories, user_id: UserId, world_id: WorldId, entity_id: EntityId
) -> EntityAccess:
    """A user's access to an entity: fetched from the repos, decided by `permissions`."""
    entity = await repos.entities.get(world_id, entity_id)
    if entity is None:
        raise EntityNotFoundError(entity_id)

    world = await repos.worlds.get(world_id)
    if world is not None and permissions.is_owner(world, user_id):
        return FULL_ACCESS

    ancestor_ids = await repos.entities.get_ancestor_ids(world_id, entity_id)
    grants = await repos.permissions.get_grants(world_id, user_id)
    return permissions.resolve_access(entity_id, ancestor_ids, grants)
