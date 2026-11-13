from enum import StrEnum

from pydantic import BaseModel, Field


class UserRole(StrEnum):
    ADMIN = "admin"
    WARDEN = "warden"
    MEMBER = "member"


class User(BaseModel):
    name: str
    email: str
    hashed_password: str
    role: UserRole


EntityId = str
WorldId = str


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
    parent: EntityId
    children: list[EntityId] = Field(default_factory=list)

    article: Article | None = None
    map: Map | None = None


class World(BaseModel):
    name: str
    description: str | None = None
    pic: str | None = None
