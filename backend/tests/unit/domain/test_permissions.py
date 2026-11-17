import pytest

from app.domain.models import PermissionLevel, World
from app.domain.permissions import EntityAccess, is_owner, resolve_access, resolve_permission


class TestIsOwner:
    def test_true_when_user_is_the_world_owner(self):
        world = World(id="w1", owner_id="u1", name="World")

        assert is_owner(world, "u1") is True

    def test_false_when_user_is_not_the_world_owner(self):
        world = World(id="w1", owner_id="u1", name="World")

        assert is_owner(world, "u2") is False


class TestResolvePermission:
    def test_self_grant_wins_over_ancestor_grant(self):
        grants = {"entity": PermissionLevel.WRITE, "parent": PermissionLevel.READ}

        level = resolve_permission("entity", ["parent"], grants)

        assert level is PermissionLevel.WRITE

    def test_falls_back_to_closest_ancestor_grant(self):
        grants = {"grandparent": PermissionLevel.READ}

        level = resolve_permission("entity", ["parent", "grandparent"], grants)

        assert level is PermissionLevel.READ

    def test_closest_ancestor_wins_over_a_farther_one(self):
        grants = {"parent": PermissionLevel.READ, "grandparent": PermissionLevel.WRITE}

        level = resolve_permission("entity", ["parent", "grandparent"], grants)

        assert level is PermissionLevel.READ

    def test_grant_on_a_descendant_never_leaks_up_to_an_ancestor(self):
        grants = {"child": PermissionLevel.WRITE}

        level = resolve_permission("entity", ["parent", "grandparent"], grants)

        assert level is None

    def test_no_grant_anywhere_returns_none(self):
        level = resolve_permission("entity", ["parent", "grandparent"], {})

        assert level is None

    def test_root_entity_with_no_self_grant_returns_none(self):
        level = resolve_permission("entity", [], {"other": PermissionLevel.WRITE})

        assert level is None


class TestResolveAccess:
    def test_no_grants_anywhere_denies_everything(self):
        access = resolve_access("entity", ["parent", "grandparent"], {})

        assert access == EntityAccess(read=False, write=False, can_delete=False)

    def test_read_grant_allows_read_but_not_write(self):
        access = resolve_access("entity", ["parent"], {"entity": PermissionLevel.READ})

        assert access.read is True
        assert access.write is False

    def test_can_delete_resolves_against_parents_own_ancestor_chain_not_childs_level(self):
        """WRITE at grandparent, READ at parent, nothing on the entity itself.

        The entity's own effective level is READ (nearest wins), so write=False.
        can_delete must resolve to the parent's own direct READ grant, not fall
        through to the grandparent's WRITE.
        """
        grants = {
            "parent": PermissionLevel.READ,
            "grandparent": PermissionLevel.WRITE,
        }

        access = resolve_access("entity", ["parent", "grandparent"], grants)

        assert access.read is True
        assert access.write is False
        assert access.can_delete is False

    def test_can_delete_true_when_parent_itself_has_a_write_grant(self):
        grants = {
            "entity": PermissionLevel.WRITE,
            "parent": PermissionLevel.WRITE,
        }

        access = resolve_access("entity", ["parent"], grants)

        assert access.write is True
        assert access.can_delete is True

    def test_root_entity_can_never_be_deleted_even_with_a_grant_on_itself(self):
        access = resolve_access("entity", [], {"entity": PermissionLevel.WRITE})

        assert access.write is True
        assert access.can_delete is False


@pytest.mark.parametrize("level", [PermissionLevel.READ, PermissionLevel.WRITE])
def test_resolve_access_read_is_true_for_any_grant_level(level):
    access = resolve_access("entity", [], {"entity": level})

    assert access.read is True
