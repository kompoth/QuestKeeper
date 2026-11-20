"""SQLAlchemy adapters implementing the domain repository ports."""

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.db.orm import (
    ArticleRow,
    EntityPermissionRow,
    EntityRow,
    MapPinRow,
    MapRow,
    PasswordResetRow,
    RegistrationConfirmationRow,
    RuntimeSettingsRow,
    SessionRow,
    UserRow,
    WorldInviteRow,
    WorldRow,
)
from app.domain.models import (
    Article,
    Entity,
    EntityId,
    EntityPermission,
    Map,
    MapPin,
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
from app.services.access import EmailAlreadyRegisteredError, IdCollisionError, UserNotFoundError

_RUNTIME_SETTINGS_ID = "singleton"


class InviteNotFoundError(Exception):
    pass


async def _upsert(
    session: AsyncSession,
    table: Any,  # noqa: ANN401 -- an ORM-mapped class; sqlalchemy's insert() has no precise shared type
    values: Mapping[str, object],
    *,
    update_columns: Sequence[str],
) -> None:
    """Inserts `values`, or updates `update_columns` in place if a row already matches a unique key."""
    update_values = {column: values[column] for column in update_columns}
    stmt = mysql_insert(table).values(**values).on_duplicate_key_update(**update_values)
    await session.execute(stmt)


def _apply_search(query: Any, search: str | None) -> Any:  # noqa: ANN401 -- a Select of unspecified result shape
    """Restricts `query` to users whose name or email contains `search` (case-insensitive), if given."""
    if not search:
        return query
    pattern = f"%{search}%"
    return query.where(or_(UserRow.name.ilike(pattern), UserRow.email.ilike(pattern)))


def _user_from_row(row: UserRow) -> User:
    return User(
        id=row.id,
        name=row.name,
        email=row.email,
        hashed_password=row.hashed_password,
        role=row.role,
        status=row.status,
        joined_at=row.joined_at,
    )


def _invite_from_row(row: WorldInviteRow) -> WorldInvite:
    return WorldInvite(
        id=row.id,
        world_id=row.world_id,
        invitee_id=row.invitee_id,
        accepted=row.accepted,
        confirmation_token=row.confirmation_token,
        token_expires_at=row.token_expires_at,
    )


def _world_from_row(row: WorldRow) -> World:
    return World(
        id=row.id,
        owner_id=row.owner_id,
        name=row.name,
        description=row.description,
        pic=row.pic,
        created_at=row.created_at,
    )


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
        deleted_at=row.deleted_at,
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

    async def create(self, user: User) -> None:
        self._session.add(
            UserRow(
                id=user.id,
                name=user.name,
                email=user.email,
                hashed_password=user.hashed_password,
                role=user.role,
                status=user.status,
                joined_at=user.joined_at,
            )
        )
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise EmailAlreadyRegisteredError(user.email) from exc

    async def update_password(self, user_id: UserId, hashed_password: str) -> None:
        row = await self._session.get(UserRow, user_id)
        if row is None:
            raise RuntimeError(f"update_password() called for a user that doesn't exist: {user_id}")
        row.hashed_password = hashed_password

    async def list_page(self, offset: int, limit: int, search: str | None = None) -> Sequence[User]:
        query = select(UserRow).order_by(UserRow.email).offset(offset).limit(limit)
        result = await self._session.execute(_apply_search(query, search))
        return [_user_from_row(row) for row in result.scalars()]

    async def count(self, search: str | None = None) -> int:
        query = select(func.count()).select_from(UserRow)
        result = await self._session.execute(_apply_search(query, search))
        return result.scalar_one()

    async def update_role(self, user_id: UserId, role: UserRole) -> None:
        row = await self._session.get(UserRow, user_id)
        if row is None:
            raise UserNotFoundError(user_id)
        row.role = role

    async def update_status(self, user_id: UserId, status: UserStatus) -> None:
        row = await self._session.get(UserRow, user_id)
        if row is None:
            raise UserNotFoundError(user_id)
        row.status = status

    async def has_admin(self) -> bool:
        result = await self._session.execute(
            select(UserRow.id).where(UserRow.role == UserRole.ADMIN, UserRow.status == UserStatus.ACTIVE).limit(1)
        )
        return result.first() is not None

    async def update_registration_pending(self, user_id: UserId, name: str, hashed_password: str) -> None:
        row = await self._session.get(UserRow, user_id)
        if row is None:
            raise UserNotFoundError(user_id)
        row.name = name
        row.hashed_password = hashed_password

    async def claim(self, user_id: UserId, name: str, hashed_password: str) -> None:
        row = await self._session.get(UserRow, user_id)
        if row is None:
            raise UserNotFoundError(user_id)
        row.name = name
        row.hashed_password = hashed_password
        row.status = UserStatus.ACTIVE


class SqlWorldRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, world_id: WorldId) -> World | None:
        row = await self._session.get(WorldRow, world_id)
        if row is None or row.deleted_at is not None:
            return None
        return _world_from_row(row)

    async def list_for_user(self, user_id: UserId) -> Sequence[World]:
        owned = await self._session.execute(
            select(WorldRow).where(WorldRow.owner_id == user_id, WorldRow.deleted_at.is_(None))
        )
        worlds_by_id = {row.id: row for row in owned.scalars()}

        granted = await self._session.execute(
            select(WorldRow)
            .join(EntityRow, EntityRow.world_id == WorldRow.id)
            .join(EntityPermissionRow, EntityPermissionRow.entity_id == EntityRow.id)
            .where(EntityPermissionRow.user_id == user_id, WorldRow.deleted_at.is_(None))
            .distinct()
        )
        for row in granted.scalars():
            worlds_by_id.setdefault(row.id, row)

        worlds = [_world_from_row(row) for row in worlds_by_id.values()]
        return sorted(worlds, key=lambda world: world.created_at or datetime.min.replace(tzinfo=UTC))

    async def create(self, world: World) -> None:
        self._session.add(
            WorldRow(
                id=world.id,
                owner_id=world.owner_id,
                name=world.name,
                description=world.description,
                created_at=world.created_at or datetime.now(UTC),
                pic=world.pic,
            )
        )
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise IdCollisionError(world.id) from exc

    async def update(self, world: World) -> None:
        row = await self._session.get(WorldRow, world.id)
        if row is None:
            raise RuntimeError(f"update() called for a world that doesn't exist: {world.id}")
        row.name = world.name
        row.description = world.description
        row.pic = world.pic

    async def delete(self, world_id: WorldId) -> None:
        await self._session.execute(
            update(WorldRow).where(WorldRow.id == world_id).values(deleted_at=datetime.now(UTC))
        )


class SqlEntityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, world_id: WorldId, entity_id: EntityId, *, include_deleted: bool = False) -> Entity | None:
        # populate_existing forces a fresh eager-load of article/map every call. Without it, a `get()`
        # for an entity already in this session's identity map (e.g. after a sibling set_article/set_map
        # mutation expired its relationship attributes) falls back to lazy-loading on access in
        # `_entity_from_row`, which can't bridge into an active greenlet from inside ASGI dispatch.
        row = await self._session.get(
            EntityRow,
            entity_id,
            options=[selectinload(EntityRow.article), selectinload(EntityRow.map).selectinload(MapRow.pins)],
            populate_existing=True,
        )
        if row is None or row.world_id != world_id:
            return None
        if not include_deleted and row.deleted_at is not None:
            return None

        result = await self._session.execute(
            select(EntityRow.id).where(EntityRow.parent_id == entity_id, EntityRow.deleted_at.is_(None))
        )
        return _entity_from_row(row, result.scalars().all())

    async def list_for_world(self, world_id: WorldId) -> Sequence[Entity]:
        result = await self._session.execute(
            select(EntityRow)
            .where(EntityRow.world_id == world_id, EntityRow.deleted_at.is_(None))
            .options(selectinload(EntityRow.article), selectinload(EntityRow.map).selectinload(MapRow.pins))
            .execution_options(populate_existing=True)
            .order_by(EntityRow.created_at)
        )
        rows = result.scalars().all()

        children_by_parent_id: dict[str, list[str]] = {}
        for row in rows:
            if row.parent_id is not None:
                children_by_parent_id.setdefault(row.parent_id, []).append(row.id)

        return [_entity_from_row(row, children_by_parent_id.get(row.id, [])) for row in rows]

    async def list_trash(self, world_id: WorldId) -> Sequence[Entity]:
        result = await self._session.execute(
            select(EntityRow)
            .where(EntityRow.world_id == world_id, EntityRow.deleted_at.is_not(None))
            .options(selectinload(EntityRow.article), selectinload(EntityRow.map).selectinload(MapRow.pins))
            .execution_options(populate_existing=True)
            .order_by(EntityRow.deleted_at.desc())
        )
        rows = result.scalars().all()
        deleted_ids = {row.id for row in rows}

        # Only nests a child under its tombstoned parent - a parent whose child was independently
        # restored simply stops listing it, since that child no longer appears in `rows` at all.
        children_by_parent_id: dict[str, list[str]] = {}
        for row in rows:
            if row.parent_id is not None and row.parent_id in deleted_ids:
                children_by_parent_id.setdefault(row.parent_id, []).append(row.id)

        return [_entity_from_row(row, children_by_parent_id.get(row.id, [])) for row in rows]

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
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise IdCollisionError(entity_id) from exc

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

    async def _still_trashed_ancestor_ids(self, world_id: WorldId, entity_id: EntityId) -> list[EntityId]:
        """`entity_id`'s ancestor ids that are still tombstoned, closest-first, stopping at the first
        ancestor that's already alive (or at the root) - restoring past that point isn't needed, since an
        alive ancestor means the chain above it is already reachable."""
        ancestor_ids = await self.get_ancestor_ids(world_id, entity_id)
        if not ancestor_ids:
            return []

        result = await self._session.execute(
            select(EntityRow.id, EntityRow.deleted_at).where(EntityRow.id.in_(ancestor_ids))
        )
        deleted_by_id = {row.id: row.deleted_at is not None for row in result}

        still_trashed: list[EntityId] = []
        for ancestor_id in ancestor_ids:
            if not deleted_by_id.get(ancestor_id, False):
                break
            still_trashed.append(ancestor_id)
        return still_trashed

    async def restore(self, world_id: WorldId, entity_id: EntityId, actor_id: UserId) -> None:
        """Restores `entity_id` and any still-tombstoned ancestors needed to make it reachable again in
        the live tree. Still-tombstoned descendants are left in trash."""
        ids_to_restore = [entity_id, *await self._still_trashed_ancestor_ids(world_id, entity_id)]
        now = datetime.now(UTC)
        await self._session.execute(
            update(EntityRow)
            .where(EntityRow.id.in_(ids_to_restore))
            .values(deleted_at=None, updated_at=now, updated_by=actor_id)
        )

    async def restore_branch(self, world_id: WorldId, entity_id: EntityId, actor_id: UserId) -> None:
        """Restores `entity_id`, every still-tombstoned entity in its descendant subtree, and any
        still-tombstoned ancestors needed to make it reachable again in the live tree."""
        subtree_ids = {entity_id}
        frontier = [entity_id]
        while frontier:
            result = await self._session.execute(
                select(EntityRow.id).where(
                    EntityRow.parent_id.in_(frontier),
                    EntityRow.world_id == world_id,
                    EntityRow.deleted_at.is_not(None),
                )
            )
            frontier = [child_id for child_id in result.scalars() if child_id not in subtree_ids]
            subtree_ids.update(frontier)

        ids_to_restore = subtree_ids.union(await self._still_trashed_ancestor_ids(world_id, entity_id))
        now = datetime.now(UTC)
        await self._session.execute(
            update(EntityRow)
            .where(EntityRow.id.in_(ids_to_restore))
            .values(deleted_at=None, updated_at=now, updated_by=actor_id)
        )

    async def purge(self, world_id: WorldId, entity_id: EntityId) -> Sequence[EntityId]:
        """Permanently deletes `entity_id` and its entire descendant subtree (tombstoned or not),
        found the same way `delete()` finds its subtree - ignoring deleted_at, so purging an ancestor
        always takes its whole branch with it, even a part of it that was separately restored.
        """
        subtree_ids = [entity_id]
        frontier = [entity_id]
        while frontier:
            result = await self._session.execute(
                select(EntityRow.id).where(EntityRow.parent_id.in_(frontier), EntityRow.world_id == world_id)
            )
            frontier = [child_id for child_id in result.scalars() if child_id not in subtree_ids]
            subtree_ids.extend(frontier)

        # Pins can target any entity in the world, not just ones in this subtree's own map(s).
        await self._session.execute(delete(MapPinRow).where(MapPinRow.pinned_entity_id.in_(subtree_ids)))
        await self._session.execute(delete(MapPinRow).where(MapPinRow.map_entity_id.in_(subtree_ids)))
        await self._session.execute(delete(MapRow).where(MapRow.entity_id.in_(subtree_ids)))
        await self._session.execute(delete(ArticleRow).where(ArticleRow.entity_id.in_(subtree_ids)))
        await self._session.execute(delete(EntityPermissionRow).where(EntityPermissionRow.entity_id.in_(subtree_ids)))
        # entities.parent_id self-references entities.id with no ON DELETE cascade, so children must be
        # deleted before their parent - reversing BFS discovery order guarantees that at any depth.
        for child_first_id in reversed(subtree_ids):
            await self._session.execute(delete(EntityRow).where(EntityRow.id == child_first_id))

        return subtree_ids

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


class SqlEntityPermissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_grants(self, world_id: WorldId, user_id: UserId) -> Mapping[EntityId, PermissionLevel]:
        result = await self._session.execute(
            select(EntityPermissionRow)
            .join(EntityRow, EntityRow.id == EntityPermissionRow.entity_id)
            .where(EntityRow.world_id == world_id, EntityPermissionRow.user_id == user_id)
        )
        return {row.entity_id: row.level for row in result.scalars()}

    async def get_grants_for_entity(self, entity_id: EntityId) -> Sequence[EntityPermission]:
        result = await self._session.execute(
            select(EntityPermissionRow).where(EntityPermissionRow.entity_id == entity_id)
        )
        return [
            EntityPermission(user_id=row.user_id, entity_id=row.entity_id, level=row.level) for row in result.scalars()
        ]

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


class SqlSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, session: Session) -> None:
        self._session.add(SessionRow(token=session.token, user_id=session.user_id, expires_at=session.expires_at))

    async def get(self, token: str) -> Session | None:
        row = await self._session.get(SessionRow, token)
        if row is None:
            return None

        # DATETIME columns round-trip as naive on both SQLite and MySQL; every value stored here is UTC.
        expires_at = row.expires_at.replace(tzinfo=UTC) if row.expires_at.tzinfo is None else row.expires_at
        if expires_at <= datetime.now(UTC):
            return None
        return Session(token=row.token, user_id=row.user_id, expires_at=expires_at)

    async def delete(self, token: str) -> None:
        row = await self._session.get(SessionRow, token)
        if row is not None:
            await self._session.delete(row)

    async def delete_all_for_user(self, user_id: UserId) -> None:
        await self._session.execute(delete(SessionRow).where(SessionRow.user_id == user_id))


class SqlPasswordResetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, reset: PasswordReset) -> None:
        await _upsert(
            self._session,
            PasswordResetRow,
            {"user_id": reset.user_id, "token": reset.token, "expires_at": reset.expires_at},
            update_columns=["token", "expires_at"],
        )

    async def get(self, token: str) -> PasswordReset | None:
        result = await self._session.execute(select(PasswordResetRow).where(PasswordResetRow.token == token))
        row = result.scalar_one_or_none()
        if row is None:
            return None

        expires_at = row.expires_at.replace(tzinfo=UTC) if row.expires_at.tzinfo is None else row.expires_at
        if expires_at <= datetime.now(UTC):
            return None
        return PasswordReset(token=row.token, user_id=row.user_id, expires_at=expires_at)

    async def delete(self, token: str) -> None:
        result = await self._session.execute(select(PasswordResetRow).where(PasswordResetRow.token == token))
        row = result.scalar_one_or_none()
        if row is not None:
            await self._session.delete(row)


class SqlRegistrationConfirmationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, confirmation: RegistrationConfirmation) -> None:
        await _upsert(
            self._session,
            RegistrationConfirmationRow,
            {"user_id": confirmation.user_id, "token": confirmation.token, "expires_at": confirmation.expires_at},
            update_columns=["token", "expires_at"],
        )

    async def get(self, token: str) -> RegistrationConfirmation | None:
        result = await self._session.execute(
            select(RegistrationConfirmationRow).where(RegistrationConfirmationRow.token == token)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None

        expires_at = row.expires_at.replace(tzinfo=UTC) if row.expires_at.tzinfo is None else row.expires_at
        if expires_at <= datetime.now(UTC):
            return None
        return RegistrationConfirmation(token=row.token, user_id=row.user_id, expires_at=expires_at)

    async def delete(self, token: str) -> None:
        result = await self._session.execute(
            select(RegistrationConfirmationRow).where(RegistrationConfirmationRow.token == token)
        )
        row = result.scalar_one_or_none()
        if row is not None:
            await self._session.delete(row)


class SqlWorldInviteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_pending_for_user(self, user_id: UserId) -> Sequence[WorldInvite]:
        result = await self._session.execute(
            select(WorldInviteRow).where(WorldInviteRow.invitee_id == user_id, ~WorldInviteRow.accepted)
        )
        return [_invite_from_row(row) for row in result.scalars()]

    async def get_all_for_world(self, world_id: WorldId) -> Sequence[WorldInvite]:
        result = await self._session.execute(
            select(WorldInviteRow)
            .join(UserRow, UserRow.id == WorldInviteRow.invitee_id)
            .where(WorldInviteRow.world_id == world_id)
            .order_by(UserRow.email)
        )
        return [_invite_from_row(row) for row in result.scalars()]

    async def get_by_token(self, token: str) -> WorldInvite | None:
        result = await self._session.execute(select(WorldInviteRow).where(WorldInviteRow.confirmation_token == token))
        row = result.scalar_one_or_none()
        if row is None or row.accepted or row.token_expires_at is None:
            return None

        expires_at = (
            row.token_expires_at.replace(tzinfo=UTC) if row.token_expires_at.tzinfo is None else row.token_expires_at
        )
        if expires_at <= datetime.now(UTC):
            return None
        return _invite_from_row(row)

    async def create(self, invite: WorldInvite) -> WorldInvite:
        await _upsert(
            self._session,
            WorldInviteRow,
            {
                "id": invite.id,
                "world_id": invite.world_id,
                "invitee_id": invite.invitee_id,
                "accepted": invite.accepted,
                "confirmation_token": invite.confirmation_token,
                "token_expires_at": invite.token_expires_at,
            },
            update_columns=["accepted", "confirmation_token", "token_expires_at"],
        )
        result = await self._session.execute(
            select(WorldInviteRow).where(
                WorldInviteRow.world_id == invite.world_id, WorldInviteRow.invitee_id == invite.invitee_id
            )
        )
        return _invite_from_row(result.scalar_one())

    async def accept(self, invite: WorldInvite) -> None:
        result = await self._session.execute(
            select(WorldInviteRow).where(
                WorldInviteRow.world_id == invite.world_id, WorldInviteRow.invitee_id == invite.invitee_id
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise InviteNotFoundError(invite.world_id, invite.invitee_id)

        row.accepted = True

    async def delete(self, world_id: WorldId, invitee_id: UserId) -> None:
        await self._session.execute(
            delete(WorldInviteRow).where(WorldInviteRow.world_id == world_id, WorldInviteRow.invitee_id == invitee_id)
        )


class SqlRuntimeSettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self) -> RuntimeSettings:
        row = await self._session.get(RuntimeSettingsRow, _RUNTIME_SETTINGS_ID)
        if row is None:
            return RuntimeSettings(registration_enabled=True, password_reset_enabled=True)
        return RuntimeSettings(
            registration_enabled=row.registration_enabled, password_reset_enabled=row.password_reset_enabled
        )

    async def update(self, settings: RuntimeSettings) -> None:
        await _upsert(
            self._session,
            RuntimeSettingsRow,
            {
                "id": _RUNTIME_SETTINGS_ID,
                "registration_enabled": settings.registration_enabled,
                "password_reset_enabled": settings.password_reset_enabled,
            },
            update_columns=["registration_enabled", "password_reset_enabled"],
        )
