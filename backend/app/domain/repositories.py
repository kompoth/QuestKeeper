"""Persistence interfaces, implemented by app.infra."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from app.domain.models import (
    Entity,
    EntityId,
    PermissionLevel,
    User,
    UserId,
    World,
    WorldId,
    WorldInvite,
)


class UserRepository(Protocol):
    def get_by_id(self, user_id: UserId) -> User | None: ...

    def get_by_email(self, email: str) -> User | None: ...


class WorldRepository(Protocol):
    def get(self, world_id: WorldId) -> World | None: ...


class EntityRepository(Protocol):
    def get(self, world_id: WorldId, entity_id: EntityId) -> Entity | None:
        """The entity, or None if it doesn't exist or belongs to a different world."""
        ...

    def get_ancestor_ids(self, world_id: WorldId, entity_id: EntityId) -> Sequence[EntityId]:
        """Ids from the entity's parent up to the root, in that order."""
        ...


class PermissionRepository(Protocol):
    def get_grants(self, world_id: WorldId, user_id: UserId) -> Mapping[EntityId, PermissionLevel]:
        """A user's entity_id -> level grants within one world."""
        ...


class InviteRepository(Protocol):
    def get_pending_for_user(self, user_id: UserId) -> Sequence[WorldInvite]: ...

    def accept(self, invite: WorldInvite) -> None: ...


@dataclass(frozen=True)
class Repositories:
    """All repo ports bundled together, for passing around services in one argument."""

    users: UserRepository
    worlds: WorldRepository
    entities: EntityRepository
    permissions: PermissionRepository
    invites: InviteRepository
