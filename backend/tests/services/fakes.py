"""In-memory doubles for `app.domain.repositories` Protocols, used by service tests."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.domain.models import (
    Article,
    Entity,
    EntityId,
    Map,
    PermissionLevel,
    Session,
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

    async def create(self, world: World) -> None:
        self.worlds_by_id[world.id] = world

    async def update(self, world: World) -> None:
        self.worlds_by_id[world.id] = world


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

    async def create(
        self, world_id: WorldId, entity_id: EntityId, name: str, parent_id: EntityId | None, actor_id: UserId
    ) -> None:
        now = datetime.now(UTC)
        self.entities_by_id[entity_id] = Entity(
            id=entity_id,
            world_id=world_id,
            name=name,
            parent=parent_id,
            created_at=now,
            updated_at=now,
            created_by=actor_id,
            updated_by=actor_id,
        )

    async def rename(self, entity_id: EntityId, name: str, actor_id: UserId) -> None:
        self._update(entity_id, actor_id, name=name)

    async def delete(self, world_id: WorldId, entity_id: EntityId, actor_id: UserId) -> None:  # noqa: ARG002
        self.entities_by_id.pop(entity_id, None)

    async def set_article(self, entity_id: EntityId, article: Article, actor_id: UserId) -> None:
        self._update(entity_id, actor_id, article=article)

    async def clear_article(self, entity_id: EntityId, actor_id: UserId) -> None:
        self._update(entity_id, actor_id, article=None)

    async def set_map(self, entity_id: EntityId, map_: Map, actor_id: UserId) -> None:
        self._update(entity_id, actor_id, map=map_)

    async def clear_map(self, entity_id: EntityId, actor_id: UserId) -> None:
        self._update(entity_id, actor_id, map=None)

    def _update(self, entity_id: EntityId, actor_id: UserId, **fields: object) -> None:
        entity = self.entities_by_id[entity_id]
        self.entities_by_id[entity_id] = entity.model_copy(
            update={**fields, "updated_at": datetime.now(UTC), "updated_by": actor_id}
        )


@dataclass
class FakePermissionRepository:
    grants_by_user: dict[UserId, Mapping[EntityId, PermissionLevel]] = field(default_factory=dict)

    async def get_grants(self, world_id: WorldId, user_id: UserId) -> Mapping[EntityId, PermissionLevel]:  # noqa: ARG002
        return self.grants_by_user.get(user_id, {})

    async def grant(self, user_id: UserId, entity_id: EntityId, level: PermissionLevel) -> None:
        grants = dict(self.grants_by_user.get(user_id, {}))
        grants[entity_id] = level
        self.grants_by_user[user_id] = grants

    async def revoke(self, user_id: UserId, entity_id: EntityId) -> None:
        grants = dict(self.grants_by_user.get(user_id, {}))
        grants.pop(entity_id, None)
        self.grants_by_user[user_id] = grants


@dataclass
class FakeInviteRepository:
    invites: list[WorldInvite] = field(default_factory=list)

    async def get_pending_for_user(self, user_id: UserId) -> Sequence[WorldInvite]:
        return [invite for invite in self.invites if invite.invitee_id == user_id and not invite.accepted]

    async def create(self, invite: WorldInvite) -> None:
        self.invites = [
            existing
            for existing in self.invites
            if not (existing.world_id == invite.world_id and existing.invitee_id == invite.invitee_id)
        ]
        self.invites.append(invite)

    async def accept(self, invite: WorldInvite) -> None:
        self.invites.append(invite)


@dataclass
class FakeSessionRepository:
    sessions_by_token: dict[str, Session] = field(default_factory=dict)

    async def create(self, session: Session) -> None:
        self.sessions_by_token[session.token] = session

    async def get(self, token: str) -> Session | None:
        session = self.sessions_by_token.get(token)
        if session is None or session.expires_at <= datetime.now(UTC):
            return None
        return session

    async def delete(self, token: str) -> None:
        self.sessions_by_token.pop(token, None)
