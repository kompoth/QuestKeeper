"""Pure permission-resolution logic: no I/O, no storage concerns."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.domain.models import EntityId, PermissionLevel, UserId, World


def is_owner(world: World, user_id: UserId) -> bool:
    return world.owner_id == user_id


def resolve_permission(
    entity_id: EntityId,
    ancestor_ids: Sequence[EntityId],
    grants: Mapping[EntityId, PermissionLevel],
) -> PermissionLevel | None:
    """Effective permission for a user on an entity.

    `ancestor_ids` must run from the entity's parent up to the root. `grants` is
    that user's full grant map for the world. The closest ancestor-or-self grant
    wins; a grant on a descendant never widens access on an ancestor.
    """
    for candidate_id in (entity_id, *ancestor_ids):
        if candidate_id in grants:
            return grants[candidate_id]
    return None


@dataclass(frozen=True)
class EntityAccess:
    read: bool
    # Edit this entity's own content, and create a new child under it.
    write: bool
    # Delete this entity; requires WRITE on its parent, not on itself.
    can_delete: bool


def resolve_access(
    entity_id: EntityId,
    ancestor_ids: Sequence[EntityId],
    grants: Mapping[EntityId, PermissionLevel],
) -> EntityAccess:
    """A user's full access to an entity, derived from their grants.

    `ancestor_ids` must run from the entity's parent up to the root, same as
    `resolve_permission`. Does not account for world ownership - an owner has
    full access regardless of this result, so check `is_owner` first.
    """
    level = resolve_permission(entity_id, ancestor_ids, grants)
    parent_level = resolve_permission(ancestor_ids[0], ancestor_ids[1:], grants) if ancestor_ids else None
    return EntityAccess(
        read=level is not None,
        write=level is PermissionLevel.WRITE,
        can_delete=parent_level is PermissionLevel.WRITE,
    )
