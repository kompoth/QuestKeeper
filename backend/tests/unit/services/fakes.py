"""In-memory doubles for `app.domain.repositories` Protocols, used by service tests."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.domain.models import (
    Article,
    Entity,
    EntityId,
    Map,
    PasswordReset,
    PermissionLevel,
    RegistrationConfirmation,
    RuntimeSettings,
    Session,
    User,
    UserId,
    UserRole,
    UserStatus,
    World,
    WorldId,
    WorldInvite,
)
from app.services.access import EmailAlreadyRegisteredError, UserNotFoundError


@dataclass
class FakeUserRepository:
    users_by_id: dict[UserId, User] = field(default_factory=dict)

    async def get_by_id(self, user_id: UserId) -> User | None:
        return self.users_by_id.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        return next((user for user in self.users_by_id.values() if user.email == email), None)

    async def create(self, user: User) -> None:
        if any(existing.email == user.email for existing in self.users_by_id.values()):
            raise EmailAlreadyRegisteredError(user.email)
        self.users_by_id[user.id] = user

    async def update_password(self, user_id: UserId, hashed_password: str) -> None:
        self.users_by_id[user_id] = self.users_by_id[user_id].model_copy(update={"hashed_password": hashed_password})

    async def list_page(self, offset: int, limit: int, search: str | None = None) -> Sequence[User]:
        users = sorted(self._matching(search), key=lambda user: user.email)
        return users[offset : offset + limit]

    async def count(self, search: str | None = None) -> int:
        return len(self._matching(search))

    def _matching(self, search: str | None) -> list[User]:
        if not search:
            return list(self.users_by_id.values())
        needle = search.lower()
        return [u for u in self.users_by_id.values() if needle in u.name.lower() or needle in u.email.lower()]

    async def update_role(self, user_id: UserId, role: UserRole) -> None:
        if user_id not in self.users_by_id:
            raise UserNotFoundError(user_id)
        self.users_by_id[user_id] = self.users_by_id[user_id].model_copy(update={"role": role})

    async def update_status(self, user_id: UserId, status: UserStatus) -> None:
        if user_id not in self.users_by_id:
            raise UserNotFoundError(user_id)
        self.users_by_id[user_id] = self.users_by_id[user_id].model_copy(update={"status": status})

    async def has_admin(self) -> bool:
        return any(
            user.role == UserRole.ADMIN and user.status == UserStatus.ACTIVE for user in self.users_by_id.values()
        )

    async def update_registration_pending(self, user_id: UserId, name: str, hashed_password: str) -> None:
        if user_id not in self.users_by_id:
            raise UserNotFoundError(user_id)
        self.users_by_id[user_id] = self.users_by_id[user_id].model_copy(
            update={"name": name, "hashed_password": hashed_password}
        )

    async def claim(self, user_id: UserId, name: str, hashed_password: str) -> None:
        if user_id not in self.users_by_id:
            raise UserNotFoundError(user_id)
        self.users_by_id[user_id] = self.users_by_id[user_id].model_copy(
            update={"name": name, "hashed_password": hashed_password, "status": UserStatus.ACTIVE}
        )


@dataclass
class FakeWorldRepository:
    worlds_by_id: dict[WorldId, World] = field(default_factory=dict)
    granted_world_ids_by_user: dict[UserId, set[WorldId]] = field(default_factory=dict)

    async def get(self, world_id: WorldId) -> World | None:
        return self.worlds_by_id.get(world_id)

    async def list_for_user(self, user_id: UserId) -> Sequence[World]:
        granted = self.granted_world_ids_by_user.get(user_id, set())
        return [world for world in self.worlds_by_id.values() if world.owner_id == user_id or world.id in granted]

    async def create(self, world: World) -> None:
        self.worlds_by_id[world.id] = world

    async def update(self, world: World) -> None:
        self.worlds_by_id[world.id] = world

    async def delete(self, world_id: WorldId) -> None:
        self.worlds_by_id.pop(world_id, None)


@dataclass
class FakeEntityRepository:
    entities_by_id: dict[EntityId, Entity] = field(default_factory=dict)
    ancestor_ids_by_entity: dict[EntityId, Sequence[EntityId]] = field(default_factory=dict)

    async def get(self, world_id: WorldId, entity_id: EntityId) -> Entity | None:
        entity = self.entities_by_id.get(entity_id)
        if entity is None or entity.world_id != world_id:
            return None
        return entity

    async def list_for_world(self, world_id: WorldId) -> Sequence[Entity]:
        return [entity for entity in self.entities_by_id.values() if entity.world_id == world_id]

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
class FakeEntityPermissionRepository:
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
class FakeWorldInviteRepository:
    invites: list[WorldInvite] = field(default_factory=list)

    async def get_pending_for_user(self, user_id: UserId) -> Sequence[WorldInvite]:
        return [invite for invite in self.invites if invite.invitee_id == user_id and not invite.accepted]

    async def get_all_for_world(self, world_id: WorldId) -> Sequence[WorldInvite]:
        return [invite for invite in self.invites if invite.world_id == world_id]

    async def get_by_token(self, token: str) -> WorldInvite | None:
        invite = next((invite for invite in self.invites if invite.confirmation_token == token), None)
        if invite is None or invite.accepted or invite.token_expires_at is None:
            return None
        if invite.token_expires_at <= datetime.now(UTC):
            return None
        return invite

    async def create(self, invite: WorldInvite) -> WorldInvite:
        existing = next(
            (e for e in self.invites if e.world_id == invite.world_id and e.invitee_id == invite.invitee_id), None
        )
        merged = invite.model_copy(update={"id": existing.id}) if existing else invite
        self.invites = [e for e in self.invites if e is not existing]
        self.invites.append(merged)
        return merged

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

    async def delete_all_for_user(self, user_id: UserId) -> None:
        self.sessions_by_token = {
            token: session for token, session in self.sessions_by_token.items() if session.user_id != user_id
        }


@dataclass
class FakePasswordResetRepository:
    resets_by_user_id: dict[UserId, PasswordReset] = field(default_factory=dict)

    async def create(self, reset: PasswordReset) -> None:
        self.resets_by_user_id[reset.user_id] = reset

    async def get(self, token: str) -> PasswordReset | None:
        reset = next((r for r in self.resets_by_user_id.values() if r.token == token), None)
        if reset is None or reset.expires_at <= datetime.now(UTC):
            return None
        return reset

    async def delete(self, token: str) -> None:
        self.resets_by_user_id = {
            user_id: reset for user_id, reset in self.resets_by_user_id.items() if reset.token != token
        }


@dataclass
class FakeRegistrationConfirmationRepository:
    confirmations_by_user_id: dict[UserId, RegistrationConfirmation] = field(default_factory=dict)

    async def create(self, confirmation: RegistrationConfirmation) -> None:
        self.confirmations_by_user_id[confirmation.user_id] = confirmation

    async def get(self, token: str) -> RegistrationConfirmation | None:
        confirmation = next((c for c in self.confirmations_by_user_id.values() if c.token == token), None)
        if confirmation is None or confirmation.expires_at <= datetime.now(UTC):
            return None
        return confirmation

    async def delete(self, token: str) -> None:
        self.confirmations_by_user_id = {
            user_id: c for user_id, c in self.confirmations_by_user_id.items() if c.token != token
        }


@dataclass
class FakeRuntimeSettingsRepository:
    settings: RuntimeSettings = field(
        default_factory=lambda: RuntimeSettings(registration_enabled=True, password_reset_enabled=True)
    )

    async def get(self) -> RuntimeSettings:
        return self.settings

    async def update(self, settings: RuntimeSettings) -> None:
        self.settings = settings


@dataclass
class FakeMailer:
    existing_user_invites: list[tuple[str, str]] = field(default_factory=list)  # (to_email, world_name)
    new_user_invites: list[tuple[str, str, str]] = field(default_factory=list)  # (to_email, world_name, confirm_url)
    password_resets: list[tuple[str, str]] = field(default_factory=list)  # (to_email, reset_url)
    registration_confirmations: list[tuple[str, str]] = field(default_factory=list)  # (to_email, confirm_url)

    async def send_existing_user_invite(self, *, to_email: str, world_name: str) -> None:
        self.existing_user_invites.append((to_email, world_name))

    async def send_new_user_invite(self, *, to_email: str, world_name: str, confirm_url: str) -> None:
        self.new_user_invites.append((to_email, world_name, confirm_url))

    async def send_password_reset(self, *, to_email: str, reset_url: str) -> None:
        self.password_resets.append((to_email, reset_url))

    async def send_registration_confirmation(self, *, to_email: str, confirm_url: str) -> None:
        self.registration_confirmations.append((to_email, confirm_url))
