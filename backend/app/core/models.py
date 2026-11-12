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
    id: EntityId
    world_id: WorldId
    name: str

    markdown: str
    map: Map

    parent: EntityId
    children: list[EntityId] = Field(default_factory=list)


class MapPin(BaseModel):
    entity_id: EntityId
    icon: str = "mdi-compass"


class Map(BaseModel):
    id: EntityId
    world_id: WorldId
    name: str
    pic: str
    parent: EntityId
    pins: dict[tuple[float, float], MapPin] = Field(default_factory=dict)

    @property
    def children(self) -> list[EntityId]:
        return [p.entity_id for p in self.pins.values()]


class World(BaseModel):
    name: str
    description: str | None = None
    pic: str | None = None
