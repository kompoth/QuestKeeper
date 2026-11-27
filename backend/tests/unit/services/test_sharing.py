import pytest

from app.domain.models import Entity, PermissionLevel, User, UserRole, UserStatus, World, WorldInvite
from app.domain.repositories import Repositories
from app.services.errors import (
    EntityNotFoundError,
    InviteNotFoundError,
    PermissionDeniedError,
    UserNotFoundError,
    WorldNotFoundError,
)
from app.services.sharing import (
    EntityGrant,
    InheritedEntityGrant,
    accept_invite,
    accept_invite_for_world,
    create_invite,
    expel_invitee,
    get_entity_permissions,
    grant_permission,
    list_invites_for_world,
    list_pending_invites,
    revoke_permission,
)
from tests.unit.services.fakes import (
    FakeEntityRepository,
    FakeMailer,
    FakeUserRepository,
    FakeWorldInviteRepository,
    FakeWorldRepository,
)
from tests.unit.services.fakes import make_repos as _make_repos

WORLD_ID = "w1"
OWNER_ID = "owner"
OTHER_USER_ID = "other"
GRANTEE_ID = "grantee"
ENTITY_ID = "e1"
FRONTEND_ORIGIN = "http://localhost:5173"


def make_repos(
    *, world=None, entity=None, entities=None, ancestor_ids=None, users=None, invites=None, permissions=None
) -> Repositories:
    entities_by_id = dict(entities) if entities else {}
    if entity:
        entities_by_id[entity.id] = entity
    return _make_repos(
        users=FakeUserRepository(users_by_id=users or {}),
        worlds=FakeWorldRepository(worlds_by_id={world.id: world} if world else {}),
        entities=FakeEntityRepository(entities_by_id=entities_by_id, ancestor_ids_by_entity=ancestor_ids or {}),
        permissions=permissions,
        invites=invites,
    )


def make_invitee(email="grantee@example.com") -> User:
    return User(id=GRANTEE_ID, name="Grantee", email=email, hashed_password="x", role=UserRole.MEMBER)


async def test_grant_permission_succeeds_for_world_owner():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity")
    grantee = make_invitee()
    invite = WorldInvite(id="i1", world_id=WORLD_ID, invitee_id=GRANTEE_ID)
    repos = make_repos(
        world=world, entity=entity, users={GRANTEE_ID: grantee}, invites=FakeWorldInviteRepository(invites=[invite])
    )

    await grant_permission(repos, OWNER_ID, WORLD_ID, ENTITY_ID, grantee.email, PermissionLevel.WRITE)

    grants = await repos.permissions.get_grants(WORLD_ID, GRANTEE_ID)
    assert grants == {ENTITY_ID: PermissionLevel.WRITE}


async def test_grant_permission_raises_when_grantee_has_no_invite_to_the_world():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity")
    grantee = make_invitee()
    repos = make_repos(world=world, entity=entity, users={GRANTEE_ID: grantee})

    with pytest.raises(InviteNotFoundError):
        await grant_permission(repos, OWNER_ID, WORLD_ID, ENTITY_ID, grantee.email, PermissionLevel.WRITE)


async def test_grant_permission_raises_when_world_not_found():
    repos = make_repos()

    with pytest.raises(WorldNotFoundError):
        await grant_permission(repos, OWNER_ID, WORLD_ID, ENTITY_ID, "grantee@example.com", PermissionLevel.WRITE)


async def test_grant_permission_raises_when_caller_is_not_owner():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world)

    with pytest.raises(PermissionDeniedError):
        await grant_permission(repos, OTHER_USER_ID, WORLD_ID, ENTITY_ID, "grantee@example.com", PermissionLevel.WRITE)


async def test_grant_permission_raises_when_entity_not_found():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world)

    with pytest.raises(EntityNotFoundError):
        await grant_permission(repos, OWNER_ID, WORLD_ID, ENTITY_ID, "grantee@example.com", PermissionLevel.WRITE)


async def test_grant_permission_raises_when_grantee_email_unknown():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity")
    repos = make_repos(world=world, entity=entity)

    with pytest.raises(UserNotFoundError):
        await grant_permission(repos, OWNER_ID, WORLD_ID, ENTITY_ID, "nobody@example.com", PermissionLevel.WRITE)


async def test_revoke_permission_succeeds_for_world_owner():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world)
    await repos.permissions.grant(GRANTEE_ID, ENTITY_ID, PermissionLevel.WRITE)

    await revoke_permission(repos, OWNER_ID, WORLD_ID, GRANTEE_ID, ENTITY_ID)

    grants = await repos.permissions.get_grants(WORLD_ID, GRANTEE_ID)
    assert grants == {}


async def test_revoke_permission_raises_when_caller_is_not_owner():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world)

    with pytest.raises(PermissionDeniedError):
        await revoke_permission(repos, OTHER_USER_ID, WORLD_ID, GRANTEE_ID, ENTITY_ID)


async def test_get_entity_permissions_returns_direct_grant():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity")
    grantee = make_invitee()
    repos = make_repos(world=world, entity=entity, users={GRANTEE_ID: grantee})
    await repos.permissions.grant(GRANTEE_ID, ENTITY_ID, PermissionLevel.WRITE)

    view = await get_entity_permissions(repos, OWNER_ID, WORLD_ID, ENTITY_ID)

    assert view.direct == [EntityGrant(user=grantee, level=PermissionLevel.WRITE, invite_accepted=None)]
    assert view.inherited == []


async def test_get_entity_permissions_reports_the_grantees_invite_acceptance_for_this_world():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity")
    grantee = make_invitee()
    invite = WorldInvite(id="i1", world_id=WORLD_ID, invitee_id=GRANTEE_ID, accepted=False)
    repos = make_repos(
        world=world, entity=entity, users={GRANTEE_ID: grantee}, invites=FakeWorldInviteRepository(invites=[invite])
    )
    await repos.permissions.grant(GRANTEE_ID, ENTITY_ID, PermissionLevel.WRITE)

    view = await get_entity_permissions(repos, OWNER_ID, WORLD_ID, ENTITY_ID)

    assert view.direct == [EntityGrant(user=grantee, level=PermissionLevel.WRITE, invite_accepted=False)]


async def test_get_entity_permissions_returns_inherited_grant_from_closest_ancestor():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    parent = Entity(id="parent", world_id=WORLD_ID, name="Parent")
    child = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Child", parent="parent")
    grandparent_grantee = make_invitee(email="grandparent-grant@example.com")
    parent_grantee = User(
        id="parent-grantee",
        name="Parent Grantee",
        email="parent-grant@example.com",
        hashed_password="x",
        role=UserRole.MEMBER,
    )
    repos = make_repos(
        world=world,
        entities={parent.id: parent, child.id: child},
        ancestor_ids={ENTITY_ID: ["parent", "grandparent"]},
        users={GRANTEE_ID: grandparent_grantee, "parent-grantee": parent_grantee},
    )
    await repos.permissions.grant("parent-grantee", "parent", PermissionLevel.READ)
    await repos.permissions.grant(GRANTEE_ID, "grandparent", PermissionLevel.WRITE)

    view = await get_entity_permissions(repos, OWNER_ID, WORLD_ID, ENTITY_ID)

    assert view.direct == []
    assert view.inherited == [
        InheritedEntityGrant(
            user=parent_grantee, level=PermissionLevel.READ, invite_accepted=None, from_entity_id="parent"
        ),
        InheritedEntityGrant(
            user=grandparent_grantee, level=PermissionLevel.WRITE, invite_accepted=None, from_entity_id="grandparent"
        ),
    ]


async def test_get_entity_permissions_omits_inherited_grant_overridden_by_direct_grant():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    child = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Child", parent="parent")
    grantee = make_invitee()
    repos = make_repos(world=world, entity=child, ancestor_ids={ENTITY_ID: ["parent"]}, users={GRANTEE_ID: grantee})
    await repos.permissions.grant(GRANTEE_ID, "parent", PermissionLevel.READ)
    await repos.permissions.grant(GRANTEE_ID, ENTITY_ID, PermissionLevel.WRITE)

    view = await get_entity_permissions(repos, OWNER_ID, WORLD_ID, ENTITY_ID)

    assert view.direct == [EntityGrant(user=grantee, level=PermissionLevel.WRITE, invite_accepted=None)]
    assert view.inherited == []


async def test_get_entity_permissions_raises_when_caller_is_not_owner():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity")
    repos = make_repos(world=world, entity=entity)

    with pytest.raises(PermissionDeniedError):
        await get_entity_permissions(repos, OTHER_USER_ID, WORLD_ID, ENTITY_ID)


async def test_get_entity_permissions_raises_when_entity_not_found():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world)

    with pytest.raises(EntityNotFoundError):
        await get_entity_permissions(repos, OWNER_ID, WORLD_ID, ENTITY_ID)


async def test_create_invite_succeeds_for_world_owner_and_sends_no_mail_for_an_existing_user():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world, users={GRANTEE_ID: make_invitee()})
    mailer = FakeMailer()

    invite = await create_invite(
        repos, mailer, OWNER_ID, WORLD_ID, "grantee@example.com", frontend_origin=FRONTEND_ORIGIN
    )

    assert invite.invitee_id == GRANTEE_ID
    assert invite.confirmation_token is None
    pending = await repos.invites.get_pending_for_user(GRANTEE_ID)
    assert invite in pending
    # An existing account can already see/accept the invite once logged in - no email needed.
    assert mailer.new_user_invites == []


async def test_create_invite_creates_pending_placeholder_user_and_sends_mail_when_invitee_unknown():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world)
    mailer = FakeMailer()

    invite = await create_invite(
        repos, mailer, OWNER_ID, WORLD_ID, "missing@example.com", frontend_origin=FRONTEND_ORIGIN
    )

    placeholder = await repos.users.get_by_email("missing@example.com")
    assert placeholder is not None
    assert placeholder.status == UserStatus.PENDING
    assert invite.invitee_id == placeholder.id
    assert invite.confirmation_token is not None
    assert invite.token_expires_at is not None
    assert len(mailer.new_user_invites) == 1
    to_email, world_name, confirm_url = mailer.new_user_invites[0]
    assert to_email == "missing@example.com"
    assert world_name == "World"
    assert invite.confirmation_token in confirm_url


async def test_create_invite_reuses_pending_placeholder_when_re_inviting_same_email():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    invites = FakeWorldInviteRepository()
    repos = make_repos(world=world, invites=invites)
    mailer = FakeMailer()

    first = await create_invite(
        repos, mailer, OWNER_ID, WORLD_ID, "missing@example.com", frontend_origin=FRONTEND_ORIGIN
    )
    second = await create_invite(
        repos, mailer, OWNER_ID, WORLD_ID, "missing@example.com", frontend_origin=FRONTEND_ORIGIN
    )

    assert len(invites.invites) == 1
    assert second.id == first.id
    assert second.invitee_id == first.invitee_id
    assert await repos.users.count() == 1


async def test_create_invite_raises_when_caller_is_not_owner():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world)
    mailer = FakeMailer()

    with pytest.raises(PermissionDeniedError):
        await create_invite(
            repos, mailer, OTHER_USER_ID, WORLD_ID, "grantee@example.com", frontend_origin=FRONTEND_ORIGIN
        )


async def test_list_invites_for_world_returns_all_invites_including_accepted():
    pending = WorldInvite(id="i1", world_id=WORLD_ID, invitee_id="a", accepted=False)
    accepted = WorldInvite(id="i2", world_id=WORLD_ID, invitee_id=GRANTEE_ID, accepted=True)
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world, invites=FakeWorldInviteRepository(invites=[pending, accepted]))

    result = await list_invites_for_world(repos, OWNER_ID, WORLD_ID)

    assert {invite.id for invite in result} == {pending.id, accepted.id}


async def test_list_invites_for_world_raises_when_caller_is_not_owner():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world)

    with pytest.raises(PermissionDeniedError):
        await list_invites_for_world(repos, OTHER_USER_ID, WORLD_ID)


async def test_expel_invitee_deletes_the_invite_regardless_of_acceptance():
    # expel_invitee deletes by (world_id, invitee_id) alone - accepted status never gates it.
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    invitee = make_invitee()
    invite = WorldInvite(id="i1", world_id=WORLD_ID, invitee_id=GRANTEE_ID, accepted=True)
    repos = make_repos(world=world, users={invitee.id: invitee}, invites=FakeWorldInviteRepository(invites=[invite]))

    await expel_invitee(repos, OWNER_ID, WORLD_ID, invitee.email)

    assert await repos.invites.get_all_for_world(WORLD_ID) == []


async def test_expel_invitee_raises_when_email_unknown():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world)

    with pytest.raises(InviteNotFoundError):
        await expel_invitee(repos, OWNER_ID, WORLD_ID, "nobody@example.com")


async def test_expel_invitee_raises_when_no_invite_exists_for_that_world():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    invitee = make_invitee()
    repos = make_repos(world=world, users={invitee.id: invitee})

    with pytest.raises(InviteNotFoundError):
        await expel_invitee(repos, OWNER_ID, WORLD_ID, invitee.email)


async def test_expel_invitee_raises_when_caller_is_not_owner():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    invitee = make_invitee()
    repos = make_repos(world=world, users={invitee.id: invitee})

    with pytest.raises(PermissionDeniedError):
        await expel_invitee(repos, OTHER_USER_ID, WORLD_ID, invitee.email)


async def test_accept_invite_succeeds_for_the_invitee():
    invites = FakeWorldInviteRepository()
    repos = make_repos(invites=invites)
    invite = WorldInvite(id="i1", world_id=WORLD_ID, invitee_id=GRANTEE_ID)

    await accept_invite(repos, GRANTEE_ID, invite)

    assert invite in invites.invites


async def test_accept_invite_raises_when_caller_is_not_the_invitee():
    repos = make_repos()
    invite = WorldInvite(id="i1", world_id=WORLD_ID, invitee_id=GRANTEE_ID)

    with pytest.raises(PermissionDeniedError):
        await accept_invite(repos, OTHER_USER_ID, invite)


async def test_list_pending_invites_returns_only_the_callers_pending_invites():
    invites = FakeWorldInviteRepository(
        invites=[
            WorldInvite(id="i1", world_id=WORLD_ID, invitee_id=GRANTEE_ID),
            WorldInvite(id="i2", world_id="w2", invitee_id=OTHER_USER_ID),
        ]
    )
    repos = make_repos(invites=invites)

    result = await list_pending_invites(repos, GRANTEE_ID)

    assert [invite.world_id for invite in result] == [WORLD_ID]


async def test_accept_invite_for_world_accepts_the_matching_pending_invite():
    invites = FakeWorldInviteRepository(invites=[WorldInvite(id="i1", world_id=WORLD_ID, invitee_id=GRANTEE_ID)])
    repos = make_repos(invites=invites)

    await accept_invite_for_world(repos, GRANTEE_ID, WORLD_ID)

    accepted_invite = WorldInvite(id="i1", world_id=WORLD_ID, invitee_id=GRANTEE_ID)
    assert accepted_invite in invites.invites


async def test_accept_invite_for_world_raises_when_no_pending_invite_matches():
    repos = make_repos()

    with pytest.raises(InviteNotFoundError):
        await accept_invite_for_world(repos, GRANTEE_ID, WORLD_ID)
