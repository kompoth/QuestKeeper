"""Persistence interfaces, implemented by app.infra."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from app.domain.models import (
    Article,
    Entity,
    EntityId,
    Map,
    PermissionLevel,
    User,
    UserId,
    World,
    WorldId,
    WorldInvite,
)


class UserRepository(Protocol):
    async def get_by_id(self, user_id: UserId) -> User | None: ...

    async def get_by_email(self, email: str) -> User | None: ...


class WorldRepository(Protocol):
    async def get(self, world_id: WorldId) -> World | None: ...

    async def create(self, world: World) -> None: ...

    async def update(self, world: World) -> None: ...


class EntityRepository(Protocol):
    async def get(self, world_id: WorldId, entity_id: EntityId) -> Entity | None:
        """The entity, or None if it doesn't exist, belongs to a different world, or is soft-deleted."""
        ...

    async def get_ancestor_ids(self, world_id: WorldId, entity_id: EntityId) -> Sequence[EntityId]:
        """Ids from the entity's parent up to the root, in that order."""
        ...

    async def create(
        self, world_id: WorldId, entity_id: EntityId, name: str, parent_id: EntityId | None, actor_id: UserId
    ) -> None:
        """Creates the entity, recording `actor_id` as both its creator and its latest editor."""
        ...

    async def rename(self, entity_id: EntityId, name: str, actor_id: UserId) -> None: ...

    async def delete(self, world_id: WorldId, entity_id: EntityId, actor_id: UserId) -> None:
        """Soft-deletes the entity and its entire descendant subtree (tombstone, not a hard delete)."""
        ...

    async def set_article(self, entity_id: EntityId, article: Article, actor_id: UserId) -> None:
        """Creates or replaces the entity's article facet."""
        ...

    async def clear_article(self, entity_id: EntityId, actor_id: UserId) -> None: ...

    async def set_map(self, entity_id: EntityId, map_: Map, actor_id: UserId) -> None:
        """Creates or replaces the entity's map facet, pins included."""
        ...

    async def clear_map(self, entity_id: EntityId, actor_id: UserId) -> None: ...


class PermissionRepository(Protocol):
    async def get_grants(self, world_id: WorldId, user_id: UserId) -> Mapping[EntityId, PermissionLevel]:
        """A user's entity_id -> level grants within one world."""
        ...

    async def grant(self, user_id: UserId, entity_id: EntityId, level: PermissionLevel) -> None:
        """Creates or updates (upsert) a user's grant on an entity."""
        ...

    async def revoke(self, user_id: UserId, entity_id: EntityId) -> None: ...


class InviteRepository(Protocol):
    async def get_pending_for_user(self, user_id: UserId) -> Sequence[WorldInvite]: ...

    async def create(self, invite: WorldInvite) -> None:
        """Creates the pending invite, or replaces it if one for the same (world, invitee) already exists."""
        ...

    async def accept(self, invite: WorldInvite) -> None: ...


@dataclass(frozen=True)
class Repositories:
    """All repo ports bundled together, for passing around services in one argument."""

    users: UserRepository
    worlds: WorldRepository
    entities: EntityRepository
    permissions: PermissionRepository
    invites: InviteRepository
