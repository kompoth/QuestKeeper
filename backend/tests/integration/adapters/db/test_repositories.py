from datetime import UTC, datetime, timedelta

import pytest

from app.adapters.db.orm import (
    ArticleRow,
    EntityPermissionRow,
    EntityRow,
    MapPinRow,
    MapRow,
    PasswordResetRow,
    RegistrationConfirmationRow,
    SessionRow,
    UserRow,
    WorldInviteRow,
    WorldRow,
)
from app.adapters.db.repositories import (
    InviteNotFoundError,
    SqlEntityPermissionRepository,
    SqlEntityRepository,
    SqlPasswordResetRepository,
    SqlRegistrationConfirmationRepository,
    SqlSessionRepository,
    SqlUserRepository,
    SqlWorldInviteRepository,
    SqlWorldRepository,
)
from app.domain.models import (
    Article,
    Map,
    MapPin,
    PasswordReset,
    PermissionLevel,
    RegistrationConfirmation,
    Session,
    User,
    UserRole,
    UserStatus,
    World,
    WorldInvite,
)
from app.services.errors import EmailAlreadyRegisteredError

pytestmark = pytest.mark.asyncio(loop_scope="session")


def make_user(user_id="u1", email=None) -> UserRow:
    return UserRow(
        id=user_id, name="User", email=email or f"{user_id}@example.com", hashed_password="hash", role=UserRole.MEMBER
    )


def make_world(world_id="w1", owner_id="u1") -> WorldRow:
    return WorldRow(id=world_id, owner_id=owner_id, name="World", created_at=datetime.now(UTC))


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

    async def test_create_persists_user(self, db_session):
        joined_at = datetime.now(UTC)
        user = User(
            id="u1",
            name="User",
            email="u1@example.com",
            hashed_password="hash",
            role=UserRole.MEMBER,
            joined_at=joined_at,
        )

        await SqlUserRepository(db_session).create(user)
        await db_session.commit()

        row = await db_session.get(UserRow, "u1")
        assert row is not None
        assert row.email == "u1@example.com"
        assert abs((row.joined_at.replace(tzinfo=UTC) - joined_at).total_seconds()) < 1

    async def test_update_password_changes_the_hash(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()

        await SqlUserRepository(db_session).update_password("u1", "new-hash")
        await db_session.commit()

        row = await db_session.get(UserRow, "u1")
        assert row.hashed_password == "new-hash"  # noqa: S105

    async def test_create_raises_cleanly_for_a_duplicate_email(self, db_session):
        db_session.add(make_user("u1", "dup@example.com"))
        await db_session.commit()

        duplicate = User(id="u2", name="Other", email="dup@example.com", hashed_password="hash", role=UserRole.MEMBER)
        with pytest.raises(EmailAlreadyRegisteredError):
            await SqlUserRepository(db_session).create(duplicate)

    async def test_update_registration_pending_refreshes_name_and_password(self, db_session):
        row = make_user("u1")
        row.status = UserStatus.PENDING
        db_session.add(row)
        await db_session.commit()

        await SqlUserRepository(db_session).update_registration_pending("u1", "New Name", "new-hash")
        await db_session.commit()

        updated = await db_session.get(UserRow, "u1")
        assert updated.name == "New Name"
        assert updated.hashed_password == "new-hash"  # noqa: S105
        assert updated.status == UserStatus.PENDING

    async def test_claim_activates_the_user_and_sets_name_and_password(self, db_session):
        row = make_user("u1")
        row.status = UserStatus.PENDING
        db_session.add(row)
        await db_session.commit()

        await SqlUserRepository(db_session).claim("u1", "Real Name", "new-hash")
        await db_session.commit()

        claimed = await db_session.get(UserRow, "u1")
        assert claimed.name == "Real Name"
        assert claimed.hashed_password == "new-hash"  # noqa: S105
        assert claimed.status == UserStatus.ACTIVE

    async def test_list_page_and_count_filter_by_search_on_name_or_email_case_insensitively(self, db_session):
        db_session.add(
            UserRow(id="u1", name="Alice Smith", email="alice@foo.com", hashed_password="x", role=UserRole.MEMBER)
        )
        db_session.add(
            UserRow(id="u2", name="Bob Jones", email="bob@bar.com", hashed_password="x", role=UserRole.MEMBER)
        )
        await db_session.commit()

        repo = SqlUserRepository(db_session)

        by_name = await repo.list_page(0, 10, search="ALICE")
        assert [user.id for user in by_name] == ["u1"]
        assert await repo.count(search="ALICE") == 1

        by_email = await repo.list_page(0, 10, search="bar.com")
        assert [user.id for user in by_email] == ["u2"]
        assert await repo.count(search="bar.com") == 1

        assert await repo.count() == 2


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

    async def test_list_for_user_includes_owned_and_invited_worlds(self, db_session):
        db_session.add(make_user("u1"))
        db_session.add(make_user("u2"))
        await db_session.commit()
        db_session.add(make_world("owned", "u1"))
        db_session.add(make_world("invited", "u2"))
        db_session.add(make_world("other", "u2"))
        await db_session.commit()
        # Unaccepted is enough - an invite unlocks the world itself regardless of acceptance.
        db_session.add(WorldInviteRow(id="i1", world_id="invited", invitee_id="u1"))
        await db_session.commit()

        worlds = await SqlWorldRepository(db_session).list_for_user("u1")

        assert {world.id for world in worlds} == {"owned", "invited"}

    async def test_list_for_user_excludes_a_world_with_only_an_entity_grant_and_no_invite(self, db_session):
        db_session.add(make_user("u1"))
        db_session.add(make_user("u2"))
        await db_session.commit()
        db_session.add(make_world("granted", "u2"))
        await db_session.commit()
        db_session.add(make_entity("e1", world_id="granted"))
        await db_session.commit()
        db_session.add(EntityPermissionRow(user_id="u1", entity_id="e1", level=PermissionLevel.READ))
        await db_session.commit()

        worlds = await SqlWorldRepository(db_session).list_for_user("u1")

        assert worlds == []

    async def test_list_for_user_returns_each_world_once_when_owned_and_invited(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(WorldInviteRow(id="i1", world_id="w1", invitee_id="u1"))
        await db_session.commit()

        worlds = await SqlWorldRepository(db_session).list_for_user("u1")

        assert [world.id for world in worlds] == ["w1"]


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

    async def test_list_for_world_returns_all_non_deleted_entities(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        db_session.add(make_world("w2", "u1"))
        await db_session.commit()
        db_session.add(make_entity("root", world_id="w1"))
        await db_session.commit()
        db_session.add(make_entity("child", world_id="w1", parent_id="root"))
        db_session.add(make_entity("other-world", world_id="w2"))
        await db_session.commit()

        entities = await SqlEntityRepository(db_session).list_for_world("w1")

        assert {entity.id for entity in entities} == {"root", "child"}
        root = next(entity for entity in entities if entity.id == "root")
        assert root.children == ["child"]

    async def test_list_for_world_excludes_deleted_entities(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(make_entity("e1", world_id="w1"))
        await db_session.commit()

        await SqlEntityRepository(db_session).delete("w1", "e1", "u1")
        await db_session.commit()

        entities = await SqlEntityRepository(db_session).list_for_world("w1")

        assert entities == []

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

    async def test_list_trash_returns_only_deleted_entities(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        alive = make_entity("alive", world_id="w1")
        deleted = make_entity("deleted", world_id="w1")
        deleted.deleted_at = datetime.now(UTC)
        db_session.add(alive)
        db_session.add(deleted)
        await db_session.commit()

        trash = await SqlEntityRepository(db_session).list_trash("w1")

        assert [entity.id for entity in trash] == ["deleted"]

    async def test_restore_also_restores_still_trashed_ancestors(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        parent = make_entity("parent", world_id="w1")
        parent.deleted_at = datetime.now(UTC)
        child = make_entity("child", world_id="w1", parent_id="parent")
        child.deleted_at = datetime.now(UTC)
        db_session.add(parent)
        db_session.add(child)
        await db_session.commit()

        await SqlEntityRepository(db_session).restore("w1", "child", "u1")
        await db_session.commit()

        assert await SqlEntityRepository(db_session).get("w1", "child") is not None
        assert await SqlEntityRepository(db_session).get("w1", "parent") is not None

    async def test_restore_stops_at_first_alive_ancestor(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        grandparent = make_entity("grandparent", world_id="w1")
        parent = make_entity("parent", world_id="w1", parent_id="grandparent")
        parent.deleted_at = datetime.now(UTC)
        child = make_entity("child", world_id="w1", parent_id="parent")
        child.deleted_at = datetime.now(UTC)
        db_session.add(grandparent)
        db_session.add(parent)
        db_session.add(child)
        await db_session.commit()

        await SqlEntityRepository(db_session).restore("w1", "child", "u1")
        await db_session.commit()

        row = await db_session.get(EntityRow, "grandparent")
        assert row.updated_by == "u1"  # unchanged from make_entity()'s creator - never touched

    async def test_restore_does_not_restore_descendants(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        parent = make_entity("parent", world_id="w1")
        parent.deleted_at = datetime.now(UTC)
        child = make_entity("child", world_id="w1", parent_id="parent")
        child.deleted_at = datetime.now(UTC)
        db_session.add(parent)
        db_session.add(child)
        await db_session.commit()

        await SqlEntityRepository(db_session).restore("w1", "parent", "u1")
        await db_session.commit()

        assert await SqlEntityRepository(db_session).get("w1", "parent") is not None
        assert await SqlEntityRepository(db_session).get("w1", "child") is None

    async def test_restore_branch_restores_descendants_and_ancestors(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        parent = make_entity("parent", world_id="w1")
        parent.deleted_at = datetime.now(UTC)
        entity = make_entity("entity", world_id="w1", parent_id="parent")
        entity.deleted_at = datetime.now(UTC)
        child = make_entity("child", world_id="w1", parent_id="entity")
        child.deleted_at = datetime.now(UTC)
        db_session.add(parent)
        db_session.add(entity)
        db_session.add(child)
        await db_session.commit()

        await SqlEntityRepository(db_session).restore_branch("w1", "entity", "u1")
        await db_session.commit()

        assert await SqlEntityRepository(db_session).get("w1", "parent") is not None
        assert await SqlEntityRepository(db_session).get("w1", "entity") is not None
        assert await SqlEntityRepository(db_session).get("w1", "child") is not None

    async def test_purge_permanently_removes_entity_and_descendants(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        entity = make_entity("entity", world_id="w1")
        entity.deleted_at = datetime.now(UTC)
        child = make_entity("child", world_id="w1", parent_id="entity")
        child.deleted_at = datetime.now(UTC)
        db_session.add(entity)
        db_session.add(child)
        await db_session.commit()

        await SqlEntityRepository(db_session).purge("w1", "entity")
        await db_session.commit()

        assert await db_session.get(EntityRow, "entity") is None
        assert await db_session.get(EntityRow, "child") is None

    async def test_purge_removes_article_map_pins_and_permissions(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        entity = make_entity("entity", world_id="w1")
        entity.deleted_at = datetime.now(UTC)
        db_session.add(entity)
        await db_session.commit()
        db_session.add(ArticleRow(entity_id="entity", markdown="# Hi"))
        db_session.add(MapRow(entity_id="entity", pic="map.png"))
        db_session.add(MapPinRow(map_entity_id="entity", x=1, y=2, pinned_entity_id="entity"))
        db_session.add(EntityPermissionRow(user_id="u1", entity_id="entity", level=PermissionLevel.WRITE))
        await db_session.commit()

        await SqlEntityRepository(db_session).purge("w1", "entity")
        await db_session.commit()

        assert await db_session.get(ArticleRow, "entity") is None
        assert await db_session.get(MapRow, "entity") is None
        assert await db_session.get(EntityPermissionRow, ("u1", "entity")) is None

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
        # MySQL's DATETIME column truncates to whole seconds, unlike the in-memory value.
        assert abs((found.expires_at - expires_at).total_seconds()) < 1

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

    async def test_delete_all_for_user_removes_only_that_users_sessions(self, db_session):
        db_session.add(make_user("u1"))
        db_session.add(make_user("u2"))
        await db_session.commit()
        expires_at = datetime.now(UTC) + timedelta(days=1)
        db_session.add(SessionRow(token="tok1", user_id="u1", expires_at=expires_at))
        db_session.add(SessionRow(token="tok2", user_id="u1", expires_at=expires_at))
        db_session.add(SessionRow(token="tok3", user_id="u2", expires_at=expires_at))
        await db_session.commit()

        await SqlSessionRepository(db_session).delete_all_for_user("u1")
        await db_session.commit()

        assert await db_session.get(SessionRow, "tok1") is None
        assert await db_session.get(SessionRow, "tok2") is None
        assert await db_session.get(SessionRow, "tok3") is not None


class TestSqlPasswordResetRepository:
    async def test_create_and_get_round_trips_a_reset(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()

        expires_at = datetime.now(UTC) + timedelta(hours=1)
        reset = PasswordReset(token="tok", user_id="u1", expires_at=expires_at)
        await SqlPasswordResetRepository(db_session).create(reset)
        await db_session.commit()

        found = await SqlPasswordResetRepository(db_session).get("tok")
        assert found is not None
        assert found.user_id == "u1"
        # MySQL's DATETIME column truncates to whole seconds, unlike the in-memory value.
        assert abs((found.expires_at - expires_at).total_seconds()) < 1

    async def test_get_returns_none_when_token_does_not_exist(self, db_session):
        found = await SqlPasswordResetRepository(db_session).get("missing")

        assert found is None

    async def test_get_returns_none_for_an_expired_reset(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(PasswordResetRow(token="tok", user_id="u1", expires_at=datetime.now(UTC) - timedelta(seconds=1)))
        await db_session.commit()

        found = await SqlPasswordResetRepository(db_session).get("tok")

        assert found is None

    async def test_delete_removes_the_reset(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(PasswordResetRow(token="tok", user_id="u1", expires_at=datetime.now(UTC) + timedelta(hours=1)))
        await db_session.commit()

        await SqlPasswordResetRepository(db_session).delete("tok")
        await db_session.commit()

        assert await db_session.get(PasswordResetRow, "tok") is None

    async def test_delete_is_a_no_op_when_token_does_not_exist(self, db_session):
        await SqlPasswordResetRepository(db_session).delete("missing")

    async def test_create_for_the_same_user_replaces_the_outstanding_token(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()

        repo = SqlPasswordResetRepository(db_session)
        first = PasswordReset(token="first-tok", user_id="u1", expires_at=datetime.now(UTC) + timedelta(hours=1))
        await repo.create(first)
        await db_session.commit()

        second = PasswordReset(token="second-tok", user_id="u1", expires_at=datetime.now(UTC) + timedelta(hours=1))
        await repo.create(second)
        await db_session.commit()

        assert await repo.get("first-tok") is None
        found = await repo.get("second-tok")
        assert found is not None
        assert found.user_id == "u1"


class TestSqlRegistrationConfirmationRepository:
    async def test_create_and_get_round_trips_a_confirmation(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()

        expires_at = datetime.now(UTC) + timedelta(hours=24)
        confirmation = RegistrationConfirmation(token="tok", user_id="u1", expires_at=expires_at)
        await SqlRegistrationConfirmationRepository(db_session).create(confirmation)
        await db_session.commit()

        found = await SqlRegistrationConfirmationRepository(db_session).get("tok")
        assert found is not None
        assert found.user_id == "u1"

    async def test_get_returns_none_when_token_does_not_exist(self, db_session):
        found = await SqlRegistrationConfirmationRepository(db_session).get("missing")

        assert found is None

    async def test_get_returns_none_for_an_expired_confirmation(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(
            RegistrationConfirmationRow(token="tok", user_id="u1", expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
        await db_session.commit()

        found = await SqlRegistrationConfirmationRepository(db_session).get("tok")

        assert found is None

    async def test_delete_removes_the_confirmation(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(
            RegistrationConfirmationRow(token="tok", user_id="u1", expires_at=datetime.now(UTC) + timedelta(hours=24))
        )
        await db_session.commit()

        await SqlRegistrationConfirmationRepository(db_session).delete("tok")
        await db_session.commit()

        assert await db_session.get(RegistrationConfirmationRow, "tok") is None

    async def test_delete_is_a_no_op_when_token_does_not_exist(self, db_session):
        await SqlRegistrationConfirmationRepository(db_session).delete("missing")

    async def test_create_for_the_same_user_replaces_the_outstanding_token(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()

        repo = SqlRegistrationConfirmationRepository(db_session)
        first = RegistrationConfirmation(
            token="first-tok", user_id="u1", expires_at=datetime.now(UTC) + timedelta(hours=24)
        )
        await repo.create(first)
        await db_session.commit()

        second = RegistrationConfirmation(
            token="second-tok", user_id="u1", expires_at=datetime.now(UTC) + timedelta(hours=24)
        )
        await repo.create(second)
        await db_session.commit()

        assert await repo.get("first-tok") is None
        found = await repo.get("second-tok")
        assert found is not None
        assert found.user_id == "u1"


class TestSqlEntityPermissionRepository:
    async def test_get_grants_returns_mapping_for_user_in_world(self, db_session):
        db_session.add(make_user("u1"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(make_entity("e1", world_id="w1"))
        await db_session.commit()
        db_session.add(EntityPermissionRow(user_id="u1", entity_id="e1", level=PermissionLevel.WRITE))
        await db_session.commit()

        grants = await SqlEntityPermissionRepository(db_session).get_grants("w1", "u1")

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

        grants = await SqlEntityPermissionRepository(db_session).get_grants("w1", "u1")

        assert grants == {"e1": PermissionLevel.READ}

    async def test_get_grants_for_entity_returns_every_grant_on_that_entity(self, db_session):
        db_session.add(make_user("u1"))
        db_session.add(make_user("u2"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(make_entity("e1", world_id="w1"))
        db_session.add(make_entity("e2", world_id="w1"))
        await db_session.commit()
        db_session.add(EntityPermissionRow(user_id="u1", entity_id="e1", level=PermissionLevel.READ))
        db_session.add(EntityPermissionRow(user_id="u2", entity_id="e1", level=PermissionLevel.WRITE))
        db_session.add(EntityPermissionRow(user_id="u1", entity_id="e2", level=PermissionLevel.WRITE))
        await db_session.commit()

        grants = await SqlEntityPermissionRepository(db_session).get_grants_for_entity("e1")

        assert {(grant.user_id, grant.level) for grant in grants} == {
            ("u1", PermissionLevel.READ),
            ("u2", PermissionLevel.WRITE),
        }

    async def test_grant_creates_a_new_grant(self, db_session):
        db_session.add(make_user("u1"))
        db_session.add(make_user("grantee"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(make_entity("e1", world_id="w1"))
        await db_session.commit()

        await SqlEntityPermissionRepository(db_session).grant("grantee", "e1", PermissionLevel.READ)
        await db_session.commit()

        grants = await SqlEntityPermissionRepository(db_session).get_grants("w1", "grantee")
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

        await SqlEntityPermissionRepository(db_session).grant("grantee", "e1", PermissionLevel.WRITE)
        await db_session.commit()

        grants = await SqlEntityPermissionRepository(db_session).get_grants("w1", "grantee")
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

        await SqlEntityPermissionRepository(db_session).revoke("grantee", "e1")
        await db_session.commit()

        grants = await SqlEntityPermissionRepository(db_session).get_grants("w1", "grantee")
        assert grants == {}

    async def test_revoke_is_a_no_op_when_no_grant_exists(self, db_session):
        db_session.add(make_user("u1"))
        db_session.add(make_user("grantee"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(make_entity("e1", world_id="w1"))
        await db_session.commit()

        await SqlEntityPermissionRepository(db_session).revoke("grantee", "e1")
        await db_session.commit()


class TestSqlWorldInviteRepository:
    async def test_get_pending_for_user_excludes_accepted_invites(self, db_session):
        db_session.add(make_user("u1"))
        db_session.add(make_user("invitee"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        db_session.add(make_world("w2", "u1"))
        await db_session.commit()
        db_session.add(WorldInviteRow(id="i1", world_id="w1", invitee_id="invitee", accepted=False))
        db_session.add(WorldInviteRow(id="i2", world_id="w2", invitee_id="invitee", accepted=True))
        await db_session.commit()

        invites = await SqlWorldInviteRepository(db_session).get_pending_for_user("invitee")

        assert len(invites) == 1
        assert invites[0].world_id == "w1"
        assert invites[0].accepted is False

    async def test_get_all_for_world_returns_pending_and_accepted(self, db_session):
        db_session.add(make_user("u1"))
        db_session.add(make_user("a"))
        db_session.add(make_user("b"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(WorldInviteRow(id="i1", world_id="w1", invitee_id="a", accepted=False))
        db_session.add(WorldInviteRow(id="i2", world_id="w1", invitee_id="b", accepted=True))
        await db_session.commit()

        invites = await SqlWorldInviteRepository(db_session).get_all_for_world("w1")

        assert {invite.id for invite in invites} == {"i1", "i2"}

    async def test_get_by_token_returns_the_invite_for_a_valid_unexpired_token(self, db_session):
        db_session.add(make_user("u1"))
        db_session.add(make_user("a"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(
            WorldInviteRow(
                id="i1",
                world_id="w1",
                invitee_id="a",
                accepted=False,
                confirmation_token="tok",
                token_expires_at=datetime.now(UTC) + timedelta(days=1),
            )
        )
        await db_session.commit()

        invite = await SqlWorldInviteRepository(db_session).get_by_token("tok")

        assert invite is not None
        assert invite.id == "i1"

    async def test_get_by_token_returns_none_for_expired_token(self, db_session):
        db_session.add(make_user("u1"))
        db_session.add(make_user("a"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(
            WorldInviteRow(
                id="i1",
                world_id="w1",
                invitee_id="a",
                accepted=False,
                confirmation_token="tok",
                token_expires_at=datetime.now(UTC) - timedelta(seconds=1),
            )
        )
        await db_session.commit()

        invite = await SqlWorldInviteRepository(db_session).get_by_token("tok")

        assert invite is None

    async def test_get_by_token_returns_none_for_already_accepted_invite(self, db_session):
        db_session.add(make_user("u1"))
        db_session.add(make_user("invitee"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(
            WorldInviteRow(
                id="i1",
                world_id="w1",
                invitee_id="invitee",
                accepted=True,
                confirmation_token="tok",
                token_expires_at=datetime.now(UTC) + timedelta(days=1),
            )
        )
        await db_session.commit()

        invite = await SqlWorldInviteRepository(db_session).get_by_token("tok")

        assert invite is None

    async def test_accept_marks_invite_accepted(self, db_session):
        db_session.add(make_user("u1"))
        db_session.add(make_user("invitee"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(WorldInviteRow(id="i1", world_id="w1", invitee_id="invitee", accepted=False))
        await db_session.commit()

        invite = WorldInvite(id="i1", world_id="w1", invitee_id="invitee", accepted=False)
        await SqlWorldInviteRepository(db_session).accept(invite)
        await db_session.commit()

        invite_row = await db_session.get(WorldInviteRow, "i1")
        assert invite_row.accepted is True

    async def test_accept_raises_when_no_matching_invite_exists(self, db_session):
        invite = WorldInvite(id="missing", world_id="missing-world", invitee_id="missing-invitee")

        with pytest.raises(InviteNotFoundError):
            await SqlWorldInviteRepository(db_session).accept(invite)

    async def test_create_persists_a_new_invite(self, db_session):
        db_session.add(make_user("u1"))
        db_session.add(make_user("invitee"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()

        invite = WorldInvite(id="i1", world_id="w1", invitee_id="invitee")
        await SqlWorldInviteRepository(db_session).create(invite)
        await db_session.commit()

        row = await db_session.get(WorldInviteRow, "i1")
        assert row is not None
        assert row.accepted is False

    async def test_create_upserts_by_world_and_invitee_preserving_row_id(self, db_session):
        db_session.add(make_user("u1"))
        db_session.add(make_user("invitee"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(WorldInviteRow(id="original-id", world_id="w1", invitee_id="invitee", accepted=False))
        await db_session.commit()

        invite = WorldInvite(id="new-id", world_id="w1", invitee_id="invitee", accepted=True)
        await SqlWorldInviteRepository(db_session).create(invite)
        await db_session.commit()

        row = await db_session.get(WorldInviteRow, "original-id")
        assert row is not None
        assert row.accepted is True
        assert await db_session.get(WorldInviteRow, "new-id") is None

    async def test_delete_removes_the_invite_for_world_and_invitee(self, db_session):
        db_session.add(make_user("u1"))
        db_session.add(make_user("invitee"))
        await db_session.commit()
        db_session.add(make_world("w1", "u1"))
        await db_session.commit()
        db_session.add(WorldInviteRow(id="i1", world_id="w1", invitee_id="invitee", accepted=False))
        await db_session.commit()

        await SqlWorldInviteRepository(db_session).delete("w1", "invitee")
        await db_session.commit()

        assert await db_session.get(WorldInviteRow, "i1") is None

    async def test_delete_is_a_noop_when_no_matching_invite_exists(self, db_session):
        await SqlWorldInviteRepository(db_session).delete("missing-world", "missing-invitee")
