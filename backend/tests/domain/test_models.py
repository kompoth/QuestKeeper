from app.domain.models import Entity, Map, PermissionLevel, WorldInvite


def test_entity_defaults_to_no_parent_and_no_children():
    entity = Entity(id="e1", world_id="w1", name="Root")

    assert entity.parent is None
    assert entity.children == []
    assert entity.article is None
    assert entity.map is None


def test_map_defaults_to_no_pins():
    world_map = Map(pic="map.png")

    assert world_map.pins == {}


def test_world_invite_defaults_to_not_accepted():
    invite = WorldInvite(world_id="w1", invitee_id="u1", entity_id="e1", level=PermissionLevel.READ)

    assert invite.accepted is False
