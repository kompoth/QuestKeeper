from datetime import UTC, datetime, timedelta

import pytest

from app.adapters.db.orm import (
    ArticleRow,
    EntityPermissionRow,
    EntityRow,
    MapPinRow,
    MapRow,
    SessionRow,
    UserRow,
    WorldInviteRow,
    WorldRow,
)
from app.adapters.db.repositories import (
    InviteNotFoundError,
    SqlEntityRepository,
    SqlInviteRepository,
    SqlPermissionRepository,
    SqlSessionRepository,
    SqlUserRepository,
    SqlWorldRepository,
)
from app.domain.models import Article, Map, MapPin, PermissionLevel, Session, UserRole, World, WorldInvite


def make_user(user_id="u1", email=None) -> UserRow:
    return UserRow(
        id=user_id, name="User", email=email or f"{user_id}@example.com", hashed_password="hash", role=UserRole.MEMBER
    )


def make_world(world_id="w1", owner_id="u1") -> WorldRow:
    return WorldRow(id=world_id, owner_id=owner_id, name="World")


def make_entity(entity_id, world_id="w1", parent_id=None, created_by="u1") -> EntityRow:
    now = datetime.now(UTC)
    return EntityRow(
        id=entity_id,
        world_id=world_id,
        name=entity_id,
        parent_id=parent_id,
        created_at=now,
        updated_at=now,
        created_by=created_by,
        updated_by=created_by,
    )


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

    async def test_create_persists_world(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()

        world = World(id="w1", owner_id="u1", name="World", description="A tale", pic="pic.png")
        await SqlWorldRepository(db_session).create(world)
        await db_session.commit()

        row = await db_session.get(WorldRow, "w1")
        assert row is not None
        assert row.name == "World"
        assert row.description == "A tale"
        assert row.pic == "pic.png"

    async def test_update_replaces_mutable_fields(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()

        updated = World(id="w1", owner_id="u1", name="New Name", description="New description", pic="new.png")
        await SqlWorldRepository(db_session).update(updated)
        await db_session.commit()

        row = await db_session.get(WorldRow, "w1")
        assert row.name == "New Name"
        assert row.description == "New description"
        assert row.pic == "new.png"


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

    async def test_create_persists_entity_with_audit_fields(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()

        await SqlEntityRepository(db_session).create("w1", "e1", "Entity", None, "u1")
        await db_session.commit()

        row = await db_session.get(EntityRow, "e1")
        assert row is not None
        assert row.name == "Entity"
        assert row.created_by == "u1"
        assert row.updated_by == "u1"
        assert row.created_at == row.updated_at

    async def test_rename_updates_name_and_touches_audit_fields(self, db_session):
        db_session.add(make_user("u1"))
        db_session.add(make_user("editor"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(make_entity("e1", world_id="w1"))
        await db_session.commit()

        await SqlEntityRepository(db_session).rename("e1", "Renamed", "editor")
        await db_session.commit()

        row = await db_session.get(EntityRow, "e1")
        assert row.name == "Renamed"
        assert row.updated_by == "editor"
        assert row.created_by == "u1"

    async def test_delete_soft_deletes_entity_and_excludes_it_from_get(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(make_entity("e1", world_id="w1"))
        await db_session.commit()

        await SqlEntityRepository(db_session).delete("w1", "e1", "u1")
        await db_session.commit()

        row = await db_session.get(EntityRow, "e1")
        assert row.deleted_at is not None
        assert row.updated_by == "u1"
        assert await SqlEntityRepository(db_session).get("w1", "e1") is None

    async def test_delete_cascades_to_the_whole_descendant_subtree(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(make_entity("root", world_id="w1"))
        await db_session.commit()
        db_session.add(make_entity("child", world_id="w1", parent_id="root"))
        await db_session.commit()
        db_session.add(make_entity("grandchild", world_id="w1", parent_id="child"))
        await db_session.commit()

        await SqlEntityRepository(db_session).delete("w1", "root", "u1")
        await db_session.commit()

        for entity_id in ("root", "child", "grandchild"):
            row = await db_session.get(EntityRow, entity_id)
            assert row.deleted_at is not None

    async def test_delete_excludes_deleted_child_from_parents_children_list(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(make_entity("parent", world_id="w1"))
        await db_session.commit()
        db_session.add(make_entity("child-a", world_id="w1", parent_id="parent"))
        db_session.add(make_entity("child-b", world_id="w1", parent_id="parent"))
        await db_session.commit()

        await SqlEntityRepository(db_session).delete("w1", "child-a", "u1")
        await db_session.commit()

        entity = await SqlEntityRepository(db_session).get("w1", "parent")
        assert entity is not None
        assert entity.children == ["child-b"]

    async def test_set_article_creates_article_when_none_exists(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(make_entity("e1", world_id="w1"))
        await db_session.commit()

        await SqlEntityRepository(db_session).set_article("e1", Article(markdown="# Hello"), "u1")
        await db_session.commit()

        row = await db_session.get(ArticleRow, "e1")
        assert row.markdown == "# Hello"

    async def test_set_article_replaces_existing_article(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(make_entity("e1", world_id="w1"))
        await db_session.commit()
        db_session.add(ArticleRow(entity_id="e1", markdown="Old"))
        await db_session.commit()

        await SqlEntityRepository(db_session).set_article("e1", Article(markdown="New"), "u1")
        await db_session.commit()

        row = await db_session.get(ArticleRow, "e1")
        assert row.markdown == "New"

    async def test_clear_article_removes_article(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(make_entity("e1", world_id="w1"))
        await db_session.commit()
        db_session.add(ArticleRow(entity_id="e1", markdown="Old"))
        await db_session.commit()

        await SqlEntityRepository(db_session).clear_article("e1", "u1")
        await db_session.commit()

        assert await db_session.get(ArticleRow, "e1") is None

    async def test_set_map_creates_map_with_pins_when_none_exists(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(make_entity("e1", world_id="w1"))
        db_session.add(make_entity("pinned", world_id="w1"))
        await db_session.commit()

        map_ = Map(pic="map.png", pins={(1.0, 2.0): MapPin(entity_id="pinned", x=1, y=2)})
        await SqlEntityRepository(db_session).set_map("e1", map_, "u1")
        await db_session.commit()

        entity = await SqlEntityRepository(db_session).get("w1", "e1")
        assert entity is not None
        assert entity.map is not None
        assert entity.map.pic == "map.png"
        assert list(entity.map.pins.keys()) == [(1.0, 2.0)]

    async def test_set_map_replaces_pins_of_an_existing_map(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(make_entity("e1", world_id="w1"))
        db_session.add(make_entity("pinned-old", world_id="w1"))
        db_session.add(make_entity("pinned-new", world_id="w1"))
        await db_session.commit()
        db_session.add(MapRow(entity_id="e1", pic="old.png"))
        db_session.add(MapPinRow(map_entity_id="e1", x=1, y=1, pinned_entity_id="pinned-old"))
        await db_session.commit()

        map_ = Map(pic="new.png", pins={(2.0, 2.0): MapPin(entity_id="pinned-new", x=2, y=2)})
        await SqlEntityRepository(db_session).set_map("e1", map_, "u1")
        await db_session.commit()

        entity = await SqlEntityRepository(db_session).get("w1", "e1")
        assert entity is not None
        assert entity.map is not None
        assert entity.map.pic == "new.png"
        assert list(entity.map.pins.keys()) == [(2.0, 2.0)]

    async def test_clear_map_removes_map_and_its_pins(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(make_entity("e1", world_id="w1"))
        db_session.add(make_entity("pinned", world_id="w1"))
        await db_session.commit()
        db_session.add(MapRow(entity_id="e1", pic="map.png"))
        db_session.add(MapPinRow(map_entity_id="e1", x=1, y=1, pinned_entity_id="pinned"))
        await db_session.commit()

        await SqlEntityRepository(db_session).clear_map("e1", "u1")
        await db_session.commit()

        assert await db_session.get(MapRow, "e1") is None


class TestSqlSessionRepository:
    async def test_create_and_get_round_trips_a_session(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()

        expires_at = datetime.now(UTC) + timedelta(days=1)
        session = Session(token="tok", user_id="u1", expires_at=expires_at)
        await SqlSessionRepository(db_session).create(session)
        await db_session.commit()

        found = await SqlSessionRepository(db_session).get("tok")
        assert found is not None
        assert found.user_id == "u1"
        assert found.expires_at == expires_at

    async def test_get_returns_none_when_token_does_not_exist(self, db_session):
        found = await SqlSessionRepository(db_session).get("missing")

        assert found is None

    async def test_get_returns_none_for_an_expired_session(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(SessionRow(token="tok", user_id="u1", expires_at=datetime.now(UTC) - timedelta(seconds=1)))
        await db_session.commit()

        found = await SqlSessionRepository(db_session).get("tok")

        assert found is None

    async def test_delete_removes_the_session(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(SessionRow(token="tok", user_id="u1", expires_at=datetime.now(UTC) + timedelta(days=1)))
        await db_session.commit()

        await SqlSessionRepository(db_session).delete("tok")
        await db_session.commit()

        assert await db_session.get(SessionRow, "tok") is None

    async def test_delete_is_a_no_op_when_token_does_not_exist(self, db_session):
        await SqlSessionRepository(db_session).delete("missing")


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

    async def test_grant_creates_a_new_grant(self, db_session):
        db_session.add(make_user("u1"))
        db_session.add(make_user("grantee"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(make_entity("e1", world_id="w1"))
        await db_session.commit()

        await SqlPermissionRepository(db_session).grant("grantee", "e1", PermissionLevel.READ)
        await db_session.commit()

        grants = await SqlPermissionRepository(db_session).get_grants("w1", "grantee")
        assert grants == {"e1": PermissionLevel.READ}

    async def test_grant_upserts_an_existing_grant(self, db_session):
        db_session.add(make_user("u1"))
        db_session.add(make_user("grantee"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(make_entity("e1", world_id="w1"))
        await db_session.commit()
        db_session.add(EntityPermissionRow(user_id="grantee", entity_id="e1", level=PermissionLevel.READ))
        await db_session.commit()

        await SqlPermissionRepository(db_session).grant("grantee", "e1", PermissionLevel.WRITE)
        await db_session.commit()

        grants = await SqlPermissionRepository(db_session).get_grants("w1", "grantee")
        assert grants == {"e1": PermissionLevel.WRITE}

    async def test_revoke_removes_an_existing_grant(self, db_session):
        db_session.add(make_user("u1"))
        db_session.add(make_user("grantee"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(make_entity("e1", world_id="w1"))
        await db_session.commit()
        db_session.add(EntityPermissionRow(user_id="grantee", entity_id="e1", level=PermissionLevel.WRITE))
        await db_session.commit()

        await SqlPermissionRepository(db_session).revoke("grantee", "e1")
        await db_session.commit()

        grants = await SqlPermissionRepository(db_session).get_grants("w1", "grantee")
        assert grants == {}

    async def test_revoke_is_a_no_op_when_no_grant_exists(self, db_session):
        db_session.add(make_user("u1"))
        db_session.add(make_user("grantee"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(make_entity("e1", world_id="w1"))
        await db_session.commit()

        await SqlPermissionRepository(db_session).revoke("grantee", "e1")
        await db_session.commit()


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

    async def test_create_persists_a_new_invite(self, db_session):
        db_session.add(make_user("u1"))
        db_session.add(make_user("invitee"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(make_entity("e1", world_id="w1"))
        await db_session.commit()

        invite = WorldInvite(world_id="w1", invitee_id="invitee", entity_id="e1", level=PermissionLevel.READ)
        await SqlInviteRepository(db_session).create(invite)
        await db_session.commit()

        row = await db_session.get(WorldInviteRow, ("w1", "invitee"))
        assert row is not None
        assert row.level == PermissionLevel.READ
        assert row.accepted is False

    async def test_create_replaces_the_pending_invite_for_the_same_world_and_invitee(self, db_session):
        db_session.add(make_user("u1"))
        db_session.add(make_user("invitee"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(make_entity("e1", world_id="w1"))
        db_session.add(make_entity("e2", world_id="w1"))
        await db_session.commit()
        db_session.add(
            WorldInviteRow(
                world_id="w1", invitee_id="invitee", entity_id="e1", level=PermissionLevel.READ, accepted=False
            )
        )
        await db_session.commit()

        invite = WorldInvite(world_id="w1", invitee_id="invitee", entity_id="e2", level=PermissionLevel.WRITE)
        await SqlInviteRepository(db_session).create(invite)
        await db_session.commit()

        row = await db_session.get(WorldInviteRow, ("w1", "invitee"))
        assert row.entity_id == "e2"
        assert row.level == PermissionLevel.WRITE
