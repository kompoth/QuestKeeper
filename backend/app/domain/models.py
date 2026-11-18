from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class UserRole(StrEnum):
    ADMIN = "admin"
    WARDEN = "warden"
    MEMBER = "member"


class UserStatus(StrEnum):
    ACTIVE = "active"
    PENDING = "pending"
    BANNED = "banned"


UserId = str
EntityId = str
WorldId = str


class User(BaseModel):
    id: UserId
    name: str
    email: str
    hashed_password: str
    role: UserRole
    status: UserStatus = UserStatus.ACTIVE
    joined_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Session(BaseModel):
    """A logged-in session, identified by its opaque `token`."""

    token: str
    user_id: UserId
    expires_at: datetime


class Article(BaseModel):
    markdown: str


class MapPin(BaseModel):
    entity_id: EntityId
    x: int
    y: int


class Map(BaseModel):
    pic: str
    pins: dict[tuple[float, float], MapPin] = Field(default_factory=dict)


class Entity(BaseModel):
    id: EntityId
    world_id: WorldId
    name: str
    parent: EntityId | None = None
    children: list[EntityId] = Field(default_factory=list)

    article: Article | None = None
    map: Map | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by: UserId | None = None
    updated_by: UserId | None = None


class World(BaseModel):
    id: WorldId
    owner_id: UserId
    name: str
    description: str | None = None
    pic: str | None = None
    created_at: datetime | None = None


class PermissionLevel(StrEnum):
    READ = "read"
    WRITE = "write"


class EntityPermission(BaseModel):
    """Grants a user a permission level on an entity.

    Applies to the entity and its whole subtree, except where overridden by
    another grant for the same user on a descendant entity (closest wins).
    Creating a child of an entity, or deleting the entity itself, requires
    WRITE on its *parent* rather than on the entity.
    """

    user_id: UserId
    entity_id: EntityId
    level: PermissionLevel


class WorldInvite(BaseModel):
    """A pending invite to join a world, carrying the initial grant.

    `invitee_id` always points at a real `users` row - a pending placeholder (PENDING status)
    is created up front for an invitee with no account yet; its `email` is the address the
    invite was sent to. Takes effect - adding the invitee as a world member with the given
    EntityPermission - only once accepted.
    """

    id: str
    world_id: WorldId
    invitee_id: UserId
    entity_id: EntityId
    level: PermissionLevel
    accepted: bool = False
    confirmation_token: str | None = None
    token_expires_at: datetime | None = None


class PasswordReset(BaseModel):
    """A single-use, expiring token authorizing one password change."""

    token: str
    user_id: UserId
    expires_at: datetime


class RegistrationConfirmation(BaseModel):
    """A single-use, expiring token authorizing one self-registration email confirmation."""

    token: str
    user_id: UserId
    expires_at: datetime


class RuntimeSettings(BaseModel):
    """Admin-editable toggles that can change without a redeploy."""

    registration_enabled: bool
    password_reset_enabled: bool
