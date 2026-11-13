"""In-memory doubles for `app.domain.repositories` Protocols, used by service tests."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

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


@dataclass
class FakeUserRepository:
    users_by_id: dict[UserId, User] = field(default_factory=dict)

    async def get_by_id(self, user_id: UserId) -> User | None:
        return self.users_by_id.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        return next((user for user in self.users_by_id.values() if user.email == email), None)


@dataclass
class FakeWorldRepository:
    worlds_by_id: dict[WorldId, World] = field(default_factory=dict)

    async def get(self, world_id: WorldId) -> World | None:
        return self.worlds_by_id.get(world_id)


@dataclass
class FakeEntityRepository:
    entities_by_id: dict[EntityId, Entity] = field(default_factory=dict)
    ancestor_ids_by_entity: dict[EntityId, Sequence[EntityId]] = field(default_factory=dict)

    async def get(self, world_id: WorldId, entity_id: EntityId) -> Entity | None:
        entity = self.entities_by_id.get(entity_id)
        if entity is None or entity.world_id != world_id:
            return None
        return entity

    async def get_ancestor_ids(self, world_id: WorldId, entity_id: EntityId) -> Sequence[EntityId]:  # noqa: ARG002
        return self.ancestor_ids_by_entity.get(entity_id, [])


@dataclass
class FakePermissionRepository:
    grants_by_user: dict[UserId, Mapping[EntityId, PermissionLevel]] = field(default_factory=dict)

    async def get_grants(self, world_id: WorldId, user_id: UserId) -> Mapping[EntityId, PermissionLevel]:  # noqa: ARG002
        return self.grants_by_user.get(user_id, {})


@dataclass
class FakeInviteRepository:
    invites: list[WorldInvite] = field(default_factory=list)

    async def get_pending_for_user(self, user_id: UserId) -> Sequence[WorldInvite]:
        return [invite for invite in self.invites if invite.invitee_id == user_id and not invite.accepted]

    async def accept(self, invite: WorldInvite) -> None:
        self.invites.append(invite)
