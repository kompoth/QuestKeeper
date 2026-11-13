import pytest

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
from app.adapters.db.repositories import (
    InviteNotFoundError,
    SqlEntityRepository,
    SqlInviteRepository,
    SqlPermissionRepository,
    SqlUserRepository,
    SqlWorldRepository,
)
from app.domain.models import PermissionLevel, UserRole, WorldInvite


def make_user(user_id="u1", email=None) -> UserRow:
    return UserRow(
        id=user_id, name="User", email=email or f"{user_id}@example.com", hashed_password="hash", role=UserRole.MEMBER
    )


def make_world(world_id="w1", owner_id="u1") -> WorldRow:
    return WorldRow(id=world_id, owner_id=owner_id, name="World")


def make_entity(entity_id, world_id="w1", parent_id=None) -> EntityRow:
    return EntityRow(id=entity_id, world_id=world_id, name=entity_id, parent_id=parent_id)


class TestSqlUserRepository:
    async def test_get_by_id_returns_user_when_found(self, db_session):
        db_session.add(make_user("u1", "u1@example.com"))
        await db_session.commit()

        user = await SqlUserRepository(db_session).get_by_id("u1")

        assert user is not None
        assert user.id == "u1"
        assert user.email == "u1@example.com"

    async def test_get_by_id_returns_none_when_not_found(self, db_session):
        user = await SqlUserRepository(db_session).get_by_id("missing")

        assert user is None

    async def test_get_by_email_returns_user_when_found(self, db_session):
        db_session.add(make_user("u1", "u1@example.com"))
        await db_session.commit()

        user = await SqlUserRepository(db_session).get_by_email("u1@example.com")

        assert user is not None
        assert user.id == "u1"

    async def test_get_by_email_returns_none_when_not_found(self, db_session):
        user = await SqlUserRepository(db_session).get_by_email("missing@example.com")

        assert user is None


class TestSqlWorldRepository:
    async def test_get_returns_world_when_found(self, db_session):
        db_session.add(make_user("u1"))
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()

        world = await SqlWorldRepository(db_session).get("w1")

        assert world is not None
        assert world.id == "w1"
        assert world.owner_id == "u1"

    async def test_get_returns_none_when_not_found(self, db_session):
        world = await SqlWorldRepository(db_session).get("missing")

        assert world is None


class TestSqlEntityRepository:
    async def test_get_returns_none_when_entity_does_not_exist(self, db_session):
        entity = await SqlEntityRepository(db_session).get("w1", "missing")

        assert entity is None

    async def test_get_returns_none_when_entity_belongs_to_a_different_world(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(make_entity("e1", world_id="w1"))
        await db_session.commit()

        entity = await SqlEntityRepository(db_session).get("other-world", "e1")

        assert entity is None

    async def test_get_returns_entity_with_article(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(make_entity("e1", world_id="w1"))
        await db_session.commit()
        db_session.add(ArticleRow(entity_id="e1", markdown="# Hello"))
        await db_session.commit()

        entity = await SqlEntityRepository(db_session).get("w1", "e1")

        assert entity is not None
        assert entity.article is not None
        assert entity.article.markdown == "# Hello"
        assert entity.map is None

    async def test_get_returns_entity_with_map_pins(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(make_entity("e1", world_id="w1"))
        db_session.add(make_entity("pinned", world_id="w1"))
        await db_session.commit()
        db_session.add(MapRow(entity_id="e1", pic="map.png"))
        db_session.add(MapPinRow(map_entity_id="e1", x=1.5, y=2.5, pinned_entity_id="pinned"))
        await db_session.commit()

        entity = await SqlEntityRepository(db_session).get("w1", "e1")

        assert entity is not None
        assert entity.map is not None
        assert entity.map.pic == "map.png"
        assert list(entity.map.pins.keys()) == [(1.5, 2.5)]
        pin = entity.map.pins[(1.5, 2.5)]
        assert pin.entity_id == "pinned"
        assert pin.x == 1
        assert pin.y == 2

    async def test_get_populates_children_from_parent_id_query(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(make_entity("parent", world_id="w1"))
        await db_session.commit()
        db_session.add(make_entity("child-a", world_id="w1", parent_id="parent"))
        db_session.add(make_entity("child-b", world_id="w1", parent_id="parent"))
        await db_session.commit()

        entity = await SqlEntityRepository(db_session).get("w1", "parent")

        assert entity is not None
        assert set(entity.children) == {"child-a", "child-b"}

    async def test_get_ancestor_ids_returns_chain_from_parent_to_root(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(make_entity("root", world_id="w1"))
        await db_session.commit()
        db_session.add(make_entity("mid", world_id="w1", parent_id="root"))
        await db_session.commit()
        db_session.add(make_entity("leaf", world_id="w1", parent_id="mid"))
        await db_session.commit()

        ancestor_ids = await SqlEntityRepository(db_session).get_ancestor_ids("w1", "leaf")

        assert list(ancestor_ids) == ["mid", "root"]

    async def test_get_ancestor_ids_empty_for_root_entity(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(make_entity("root", world_id="w1"))
        await db_session.commit()

        ancestor_ids = await SqlEntityRepository(db_session).get_ancestor_ids("w1", "root")

        assert list(ancestor_ids) == []

    async def test_get_ancestor_ids_empty_when_world_id_does_not_match_starting_entity(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(make_entity("root", world_id="w1"))
        await db_session.commit()
        db_session.add(make_entity("leaf", world_id="w1", parent_id="root"))
        await db_session.commit()

        ancestor_ids = await SqlEntityRepository(db_session).get_ancestor_ids("other-world", "leaf")

        assert list(ancestor_ids) == []


class TestSqlPermissionRepository:
    async def test_get_grants_returns_mapping_for_user_in_world(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(make_entity("e1", world_id="w1"))
        await db_session.commit()
        db_session.add(EntityPermissionRow(user_id="u1", entity_id="e1", level=PermissionLevel.WRITE))
        await db_session.commit()

        grants = await SqlPermissionRepository(db_session).get_grants("w1", "u1")

        assert grants == {"e1": PermissionLevel.WRITE}

    async def test_get_grants_excludes_grants_in_a_different_world(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        db_session.add(make_world("w2", "u1"))
        await db_session.commit()
        db_session.add(make_entity("e1", world_id="w1"))
        db_session.add(make_entity("e2", world_id="w2"))
        await db_session.commit()
        db_session.add(EntityPermissionRow(user_id="u1", entity_id="e1", level=PermissionLevel.READ))
        db_session.add(EntityPermissionRow(user_id="u1", entity_id="e2", level=PermissionLevel.WRITE))
        await db_session.commit()

        grants = await SqlPermissionRepository(db_session).get_grants("w1", "u1")

        assert grants == {"e1": PermissionLevel.READ}


class TestSqlInviteRepository:
    async def test_get_pending_for_user_excludes_accepted_invites(self, db_session):
        db_session.add(make_user("u1"))
        db_session.add(make_user("invitee"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        db_session.add(make_world("w2", "u1"))
        await db_session.commit()
        db_session.add(make_entity("e1", world_id="w1"))
        db_session.add(make_entity("e2", world_id="w2"))
        await db_session.commit()
        db_session.add(
            WorldInviteRow(
                world_id="w1", invitee_id="invitee", entity_id="e1", level=PermissionLevel.READ, accepted=False
            )
        )
        db_session.add(
            WorldInviteRow(
                world_id="w2", invitee_id="invitee", entity_id="e2", level=PermissionLevel.WRITE, accepted=True
            )
        )
        await db_session.commit()

        invites = await SqlInviteRepository(db_session).get_pending_for_user("invitee")

        assert len(invites) == 1
        assert invites[0].world_id == "w1"
        assert invites[0].accepted is False

    async def test_accept_marks_invite_accepted_and_grants_permission(self, db_session):
        db_session.add(make_user("u1"))
        db_session.add(make_user("invitee"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(make_entity("e1", world_id="w1"))
        await db_session.commit()
        db_session.add(
            WorldInviteRow(
                world_id="w1", invitee_id="invitee", entity_id="e1", level=PermissionLevel.WRITE, accepted=False
            )
        )
        await db_session.commit()

        invite = WorldInvite(
            world_id="w1", invitee_id="invitee", entity_id="e1", level=PermissionLevel.WRITE, accepted=False
        )
        await SqlInviteRepository(db_session).accept(invite)
        await db_session.commit()

        invite_row = await db_session.get(WorldInviteRow, ("w1", "invitee"))
        assert invite_row.accepted is True

        grants = await SqlPermissionRepository(db_session).get_grants("w1", "invitee")
        assert grants == {"e1": PermissionLevel.WRITE}

    async def test_accept_raises_when_no_matching_invite_exists(self, db_session):
        invite = WorldInvite(
            world_id="missing-world", invitee_id="missing-invitee", entity_id="e1", level=PermissionLevel.READ
        )

        with pytest.raises(InviteNotFoundError):
            await SqlInviteRepository(db_session).accept(invite)
