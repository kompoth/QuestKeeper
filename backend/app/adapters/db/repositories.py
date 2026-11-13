"""SQLAlchemy adapters implementing the domain repository ports."""

from collections.abc import Mapping, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.db.orm import EntityPermissionRow, EntityRow, MapRow, UserRow, WorldInviteRow, WorldRow
from app.domain.models import (
    Article,
    Entity,
    EntityId,
    Map,
    MapPin,
    PermissionLevel,
    User,
    UserId,
    World,
    WorldId,
    WorldInvite,
)


class InviteNotFoundError(Exception):
    pass


def _user_from_row(row: UserRow) -> User:
    return User(id=row.id, name=row.name, email=row.email, hashed_password=row.hashed_password, role=row.role)


def _world_from_row(row: WorldRow) -> World:
    return World(id=row.id, owner_id=row.owner_id, name=row.name, description=row.description, pic=row.pic)


def _entity_from_row(row: EntityRow, children: Sequence[EntityId]) -> Entity:
    article = Article(markdown=row.article.markdown) if row.article else None
    world_map = (
        Map(
            pic=row.map.pic,
            pins={
                (pin.x, pin.y): MapPin(entity_id=pin.pinned_entity_id, x=int(pin.x), y=int(pin.y))
                for pin in row.map.pins
            },
        )
        if row.map
        else None
    )
    return Entity(
        id=row.id,
        world_id=row.world_id,
        name=row.name,
        parent=row.parent_id,
        children=list(children),
        article=article,
        map=world_map,
    )


class SqlUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UserId) -> User | None:
        row = await self._session.get(UserRow, user_id)
        return _user_from_row(row) if row else None

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(UserRow).where(UserRow.email == email))
        row = result.scalar_one_or_none()
        return _user_from_row(row) if row else None


class SqlWorldRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, world_id: WorldId) -> World | None:
        row = await self._session.get(WorldRow, world_id)
        return _world_from_row(row) if row else None


class SqlEntityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, world_id: WorldId, entity_id: EntityId) -> Entity | None:
        row = await self._session.get(
            EntityRow,
            entity_id,
            options=[selectinload(EntityRow.article), selectinload(EntityRow.map).selectinload(MapRow.pins)],
        )
        if row is None or row.world_id != world_id:
            return None

        result = await self._session.execute(select(EntityRow.id).where(EntityRow.parent_id == entity_id))
        return _entity_from_row(row, result.scalars().all())

    async def get_ancestor_ids(self, world_id: WorldId, entity_id: EntityId) -> Sequence[EntityId]:
        ancestor_ids: list[EntityId] = []
        current_id = entity_id
        while True:
            result = await self._session.execute(
                select(EntityRow.parent_id).where(EntityRow.id == current_id, EntityRow.world_id == world_id)
            )
            parent_id = result.scalar_one_or_none()
            if not parent_id:
                return ancestor_ids
            ancestor_ids.append(parent_id)
            current_id = parent_id


class SqlPermissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_grants(self, world_id: WorldId, user_id: UserId) -> Mapping[EntityId, PermissionLevel]:
        result = await self._session.execute(
            select(EntityPermissionRow)
            .join(EntityRow, EntityRow.id == EntityPermissionRow.entity_id)
            .where(EntityRow.world_id == world_id, EntityPermissionRow.user_id == user_id)
        )
        return {row.entity_id: row.level for row in result.scalars()}


class SqlInviteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_pending_for_user(self, user_id: UserId) -> Sequence[WorldInvite]:
        result = await self._session.execute(
            select(WorldInviteRow).where(WorldInviteRow.invitee_id == user_id, ~WorldInviteRow.accepted)
        )
        return [
            WorldInvite(
                world_id=row.world_id,
                invitee_id=row.invitee_id,
                entity_id=row.entity_id,
                level=row.level,
                accepted=row.accepted,
            )
            for row in result.scalars()
        ]

    async def accept(self, invite: WorldInvite) -> None:
        row = await self._session.get(WorldInviteRow, (invite.world_id, invite.invitee_id))
        if row is None:
            raise InviteNotFoundError(invite.world_id, invite.invitee_id)

        row.accepted = True
        self._session.add(
            EntityPermissionRow(user_id=invite.invitee_id, entity_id=invite.entity_id, level=invite.level)
        )
