from enum import StrEnum

from pydantic import BaseModel, Field


class UserRole(StrEnum):
    ADMIN = "admin"
    WARDEN = "warden"
    MEMBER = "member"


UserId = str
EntityId = str
WorldId = str


class User(BaseModel):
    id: UserId
    name: str
    email: str
    hashed_password: str
    role: UserRole


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


class World(BaseModel):
    id: WorldId
    owner_id: UserId
    name: str
    description: str | None = None
    pic: str | None = None


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

    Only issued for an existing user (looked up by email). Takes effect -
    adding the invitee as a world member with the given EntityPermission -
    only once accepted.
    """

    world_id: WorldId
    invitee_id: UserId
    entity_id: EntityId
    level: PermissionLevel
    accepted: bool = False
