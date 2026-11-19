"""Persistence interfaces, implemented by app.infra."""

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol

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


class UserRepository(Protocol):
    async def get_by_id(self, user_id: UserId) -> User | None: ...

    async def get_by_email(self, email: str) -> User | None: ...

    async def create(self, user: User) -> None:
        """Raises EmailAlreadyRegisteredError if the email is taken, including a race against a concurrent create()."""
        ...

    async def update_password(self, user_id: UserId, hashed_password: str) -> None: ...

    async def list_page(self, offset: int, limit: int, search: str | None = None) -> Sequence[User]:
        """One page of all users, ordered by email.

        If `search` is given, restricts to users whose name or email contains it (case-insensitive).
        """
        ...

    async def count(self, search: str | None = None) -> int:
        """Total number of users matching `search` (see list_page), for paginating list_page()."""
        ...

    async def has_admin(self) -> bool:
        """Whether any user currently holds the admin role - used to gate seed-admin bootstrapping."""
        ...

    async def update_role(self, user_id: UserId, role: UserRole) -> None:
        """Raises UserNotFoundError if the user doesn't exist."""
        ...

    async def update_status(self, user_id: UserId, status: UserStatus) -> None:
        """Raises UserNotFoundError if the user doesn't exist."""
        ...

    async def update_registration_pending(self, user_id: UserId, name: str, hashed_password: str) -> None:
        """Re-request case: refreshes name/password on an existing PENDING user.

        Raises UserNotFoundError if the user doesn't exist.
        """
        ...

    async def claim(self, user_id: UserId, name: str, hashed_password: str) -> None:
        """Sets name/hashed_password and status=ACTIVE.

        Raises UserNotFoundError if the user doesn't exist.
        """
        ...


class WorldRepository(Protocol):
    async def get(self, world_id: WorldId) -> World | None: ...

    async def list_for_user(self, user_id: UserId) -> Sequence[World]:
        """Worlds the user owns, plus worlds where they hold any permission grant."""
        ...

    async def create(self, world: World) -> None:
        """Raises IdCollisionError if `world.id` already exists."""
        ...

    async def update(self, world: World) -> None: ...

    async def delete(self, world_id: WorldId) -> None:
        """Soft-deletes the world; its entities are left untouched but become unreachable."""
        ...


class EntityRepository(Protocol):
    async def get(self, world_id: WorldId, entity_id: EntityId) -> Entity | None:
        """The entity, or None if it doesn't exist, belongs to a different world, or is soft-deleted."""
        ...

    async def list_for_world(self, world_id: WorldId) -> Sequence[Entity]:
        """Every non-deleted entity in the world, unfiltered by permission grants."""
        ...

    async def get_ancestor_ids(self, world_id: WorldId, entity_id: EntityId) -> Sequence[EntityId]:
        """Ids from the entity's parent up to the root, in that order."""
        ...

    async def create(
        self, world_id: WorldId, entity_id: EntityId, name: str, parent_id: EntityId | None, actor_id: UserId
    ) -> None:
        """Creates the entity, recording `actor_id` as both its creator and its latest editor.

        Raises IdCollisionError if `entity_id` already exists.
        """
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


class EntityPermissionRepository(Protocol):
    async def get_grants(self, world_id: WorldId, user_id: UserId) -> Mapping[EntityId, PermissionLevel]:
        """A user's entity_id -> level grants within one world."""
        ...

    async def grant(self, user_id: UserId, entity_id: EntityId, level: PermissionLevel) -> None:
        """Creates or updates (upsert) a user's grant on an entity."""
        ...

    async def revoke(self, user_id: UserId, entity_id: EntityId) -> None: ...


class WorldInviteRepository(Protocol):
    async def get_pending_for_user(self, user_id: UserId) -> Sequence[WorldInvite]: ...

    async def get_all_for_world(self, world_id: WorldId) -> Sequence[WorldInvite]:
        """Every invite for the world, pending or accepted - for the owner's settings view."""
        ...

    async def get_by_token(self, token: str) -> WorldInvite | None:
        """The invite for an unexpired, not-yet-accepted confirmation token, or None."""
        ...

    async def create(self, invite: WorldInvite) -> WorldInvite:
        """Creates the pending invite, or upserts in place (preserving id) if one for (world, invitee) exists.

        Returns the persisted invite - its `id` may differ from `invite.id` on an upsert.
        """
        ...

    async def accept(self, invite: WorldInvite) -> None: ...


class SessionRepository(Protocol):
    async def create(self, session: Session) -> None: ...

    async def get(self, token: str) -> Session | None:
        """The session, or None if it doesn't exist or has expired."""
        ...

    async def delete(self, token: str) -> None: ...

    async def delete_all_for_user(self, user_id: UserId) -> None: ...


class PasswordResetRepository(Protocol):
    async def create(self, reset: PasswordReset) -> None:
        """Replaces any outstanding request for the same user_id - at most one valid reset token per user."""
        ...

    async def get(self, token: str) -> PasswordReset | None:
        """The reset request, or None if it doesn't exist or has expired."""
        ...

    async def delete(self, token: str) -> None: ...


class RegistrationConfirmationRepository(Protocol):
    async def create(self, confirmation: RegistrationConfirmation) -> None:
        """Replaces any outstanding request for the same user_id - at most one valid token per user."""
        ...

    async def get(self, token: str) -> RegistrationConfirmation | None:
        """The confirmation request, or None if it doesn't exist or has expired."""
        ...

    async def delete(self, token: str) -> None: ...


class RuntimeSettingsRepository(Protocol):
    async def get(self) -> RuntimeSettings:
        """The current settings, or defaults if they've never been written."""
        ...

    async def update(self, settings: RuntimeSettings) -> None: ...


async def _noop_commit() -> None:
    return None


@dataclass(frozen=True)
class Repositories:
    """All repo ports bundled together, for passing around services in one argument."""

    users: UserRepository
    worlds: WorldRepository
    entities: EntityRepository
    permissions: EntityPermissionRepository
    invites: WorldInviteRepository
    sessions: SessionRepository
    password_resets: PasswordResetRepository
    registration_confirmations: RegistrationConfirmationRepository
    runtime_settings: RuntimeSettingsRepository
    # Durably persists writes made so far, for an operation that needs a mid-request commit point.
    commit: Callable[[], Awaitable[None]] = field(default=_noop_commit)
