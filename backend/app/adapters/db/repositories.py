"""SQLAlchemy adapters implementing the domain repository ports."""

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.db.orm import (
    ArticleRow,
    EntityPermissionRow,
    EntityRow,
    MapPinRow,
    MapRow,
    UserRow,
    WorldInviteRow,
    WorldRow,
)
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
        created_at=row.created_at,
        updated_at=row.updated_at,
        created_by=row.created_by,
        updated_by=row.updated_by,
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

    async def create(self, world: World) -> None:
        self._session.add(
            WorldRow(
                id=world.id,
                owner_id=world.owner_id,
                name=world.name,
                description=world.description,
                pic=world.pic,
            )
        )

    async def update(self, world: World) -> None:
        row = await self._session.get(WorldRow, world.id)
        if row is None:
            raise RuntimeError(f"update() called for a world that doesn't exist: {world.id}")
        row.name = world.name
        row.description = world.description
        row.pic = world.pic


class SqlEntityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, world_id: WorldId, entity_id: EntityId) -> Entity | None:
        row = await self._session.get(
            EntityRow,
            entity_id,
            options=[selectinload(EntityRow.article), selectinload(EntityRow.map).selectinload(MapRow.pins)],
        )
        if row is None or row.world_id != world_id or row.deleted_at is not None:
            return None

        result = await self._session.execute(
            select(EntityRow.id).where(EntityRow.parent_id == entity_id, EntityRow.deleted_at.is_(None))
        )
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

    async def create(
        self, world_id: WorldId, entity_id: EntityId, name: str, parent_id: EntityId | None, actor_id: UserId
    ) -> None:
        now = datetime.now(UTC)
        self._session.add(
            EntityRow(
                id=entity_id,
                world_id=world_id,
                name=name,
                parent_id=parent_id,
                created_at=now,
                updated_at=now,
                created_by=actor_id,
                updated_by=actor_id,
            )
        )

    async def rename(self, entity_id: EntityId, name: str, actor_id: UserId) -> None:
        row = await self._session.get(EntityRow, entity_id)
        if row is None:
            raise RuntimeError(f"rename() called for an entity that doesn't exist: {entity_id}")
        row.name = name
        await self._touch(entity_id, actor_id)

    async def delete(self, world_id: WorldId, entity_id: EntityId, actor_id: UserId) -> None:
        """Soft-deletes `entity_id` and its whole descendant subtree, found by repeated child lookups."""
        subtree_ids = {entity_id}
        frontier = [entity_id]
        while frontier:
            result = await self._session.execute(
                select(EntityRow.id).where(EntityRow.parent_id.in_(frontier), EntityRow.world_id == world_id)
            )
            frontier = [child_id for child_id in result.scalars() if child_id not in subtree_ids]
            subtree_ids.update(frontier)

        now = datetime.now(UTC)
        await self._session.execute(
            update(EntityRow)
            .where(EntityRow.id.in_(subtree_ids))
            .values(deleted_at=now, updated_at=now, updated_by=actor_id)
        )

    async def set_article(self, entity_id: EntityId, article: Article, actor_id: UserId) -> None:
        row = await self._session.get(ArticleRow, entity_id)
        if row is None:
            self._session.add(ArticleRow(entity_id=entity_id, markdown=article.markdown))
        else:
            row.markdown = article.markdown
        await self._touch(entity_id, actor_id)

    async def clear_article(self, entity_id: EntityId, actor_id: UserId) -> None:
        row = await self._session.get(ArticleRow, entity_id)
        if row is not None:
            await self._session.delete(row)
        await self._touch(entity_id, actor_id)

    async def set_map(self, entity_id: EntityId, map_: Map, actor_id: UserId) -> None:
        row = await self._session.get(MapRow, entity_id, options=[selectinload(MapRow.pins)])
        pins = [
            MapPinRow(map_entity_id=entity_id, x=x, y=y, pinned_entity_id=pin.entity_id)
            for (x, y), pin in map_.pins.items()
        ]
        if row is None:
            self._session.add(MapRow(entity_id=entity_id, pic=map_.pic, pins=pins))
        else:
            row.pic = map_.pic
            row.pins = pins
        await self._touch(entity_id, actor_id)

    async def clear_map(self, entity_id: EntityId, actor_id: UserId) -> None:
        row = await self._session.get(MapRow, entity_id)
        if row is not None:
            await self._session.delete(row)
        await self._touch(entity_id, actor_id)

    async def _touch(self, entity_id: EntityId, actor_id: UserId) -> None:
        """Bumps the owning entity's updated_at/updated_by after one of its facets changes."""
        row = await self._session.get(EntityRow, entity_id)
        if row is None:
            raise RuntimeError(f"_touch() called for an entity that doesn't exist: {entity_id}")
        row.updated_at = datetime.now(UTC)
        row.updated_by = actor_id


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

    async def grant(self, user_id: UserId, entity_id: EntityId, level: PermissionLevel) -> None:
        row = await self._session.get(EntityPermissionRow, (user_id, entity_id))
        if row is None:
            self._session.add(EntityPermissionRow(user_id=user_id, entity_id=entity_id, level=level))
        else:
            row.level = level

    async def revoke(self, user_id: UserId, entity_id: EntityId) -> None:
        row = await self._session.get(EntityPermissionRow, (user_id, entity_id))
        if row is not None:
            await self._session.delete(row)


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

    async def create(self, invite: WorldInvite) -> None:
        row = await self._session.get(WorldInviteRow, (invite.world_id, invite.invitee_id))
        if row is None:
            self._session.add(
                WorldInviteRow(
                    world_id=invite.world_id,
                    invitee_id=invite.invitee_id,
                    entity_id=invite.entity_id,
                    level=invite.level,
                    accepted=invite.accepted,
                )
            )
        else:
            row.entity_id = invite.entity_id
            row.level = invite.level
            row.accepted = invite.accepted

    async def accept(self, invite: WorldInvite) -> None:
        row = await self._session.get(WorldInviteRow, (invite.world_id, invite.invitee_id))
        if row is None:
            raise InviteNotFoundError(invite.world_id, invite.invitee_id)

        row.accepted = True
        self._session.add(
            EntityPermissionRow(user_id=invite.invitee_id, entity_id=invite.entity_id, level=invite.level)
        )
