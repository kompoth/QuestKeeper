import pytest

from app.domain.models import Entity, EntityPermission, PermissionLevel, User, UserRole, World, WorldInvite
from app.domain.repositories import Repositories
from app.services.access import EntityNotFoundError, InviteNotFoundError, PermissionDeniedError, WorldNotFoundError
from app.services.sharing import (
    InviteGrant,
    accept_invite,
    accept_invite_for_world,
    create_invite,
    grant_permission,
    list_invites_for_world,
    list_pending_invites,
    revoke_permission,
)
from tests.services.fakes import (
    FakeEntityRepository,
    FakeInviteRepository,
    FakeMailer,
    FakePasswordResetRepository,
    FakePendingRegistrationRepository,
    FakePermissionRepository,
    FakeSessionRepository,
    FakeUserRepository,
    FakeWorldRepository,
)

WORLD_ID = "w1"
OWNER_ID = "owner"
OTHER_USER_ID = "other"
GRANTEE_ID = "grantee"
ENTITY_ID = "e1"


def make_repos(*, world=None, entity=None, users=None, invites=None) -> Repositories:
    return Repositories(
        users=FakeUserRepository(users_by_id=users or {}),
        worlds=FakeWorldRepository(worlds_by_id={world.id: world} if world else {}),
        entities=FakeEntityRepository(entities_by_id={entity.id: entity} if entity else {}),
        permissions=FakePermissionRepository(),
        invites=invites if invites is not None else FakeInviteRepository(),
        sessions=FakeSessionRepository(),
        password_resets=FakePasswordResetRepository(),
        pending_registrations=FakePendingRegistrationRepository(),
    )


def make_invitee(email="grantee@example.com") -> User:
    return User(id=GRANTEE_ID, name="Grantee", email=email, hashed_password="x", role=UserRole.MEMBER)


async def test_grant_permission_succeeds_for_world_owner():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity")
    repos = make_repos(world=world, entity=entity)
    grant = EntityPermission(user_id=GRANTEE_ID, entity_id=ENTITY_ID, level=PermissionLevel.WRITE)

    await grant_permission(repos, OWNER_ID, WORLD_ID, grant)

    grants = await repos.permissions.get_grants(WORLD_ID, GRANTEE_ID)
    assert grants == {ENTITY_ID: PermissionLevel.WRITE}


async def test_grant_permission_raises_when_world_not_found():
    repos = make_repos()
    grant = EntityPermission(user_id=GRANTEE_ID, entity_id=ENTITY_ID, level=PermissionLevel.WRITE)

    with pytest.raises(WorldNotFoundError):
        await grant_permission(repos, OWNER_ID, WORLD_ID, grant)


async def test_grant_permission_raises_when_caller_is_not_owner():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world)
    grant = EntityPermission(user_id=GRANTEE_ID, entity_id=ENTITY_ID, level=PermissionLevel.WRITE)

    with pytest.raises(PermissionDeniedError):
        await grant_permission(repos, OTHER_USER_ID, WORLD_ID, grant)


async def test_grant_permission_raises_when_entity_not_found():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world)
    grant = EntityPermission(user_id=GRANTEE_ID, entity_id=ENTITY_ID, level=PermissionLevel.WRITE)

    with pytest.raises(EntityNotFoundError):
        await grant_permission(repos, OWNER_ID, WORLD_ID, grant)


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


async def test_create_invite_succeeds_for_world_owner_and_sends_existing_user_mail():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity")
    repos = make_repos(world=world, entity=entity, users={GRANTEE_ID: make_invitee()})
    mailer = FakeMailer()
    grant = InviteGrant(entity_id=ENTITY_ID, level=PermissionLevel.READ)

    invite = await create_invite(repos, mailer, OWNER_ID, WORLD_ID, "grantee@example.com", grant)

    assert invite.invitee_id == GRANTEE_ID
    assert invite.invitee_email == "grantee@example.com"
    assert invite.confirmation_token is None
    pending = await repos.invites.get_pending_for_user(GRANTEE_ID)
    assert invite in pending
    assert mailer.existing_user_invites == [("grantee@example.com", "World")]
    assert mailer.new_user_invites == []


async def test_create_invite_creates_pending_email_invite_and_sends_mail_when_invitee_email_unknown():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity")
    repos = make_repos(world=world, entity=entity)
    mailer = FakeMailer()
    grant = InviteGrant(entity_id=ENTITY_ID, level=PermissionLevel.READ)

    invite = await create_invite(repos, mailer, OWNER_ID, WORLD_ID, "missing@example.com", grant)

    assert invite.invitee_id is None
    assert invite.invitee_email == "missing@example.com"
    assert invite.confirmation_token is not None
    assert invite.token_expires_at is not None
    assert len(mailer.new_user_invites) == 1
    to_email, world_name, confirm_url = mailer.new_user_invites[0]
    assert to_email == "missing@example.com"
    assert world_name == "World"
    assert invite.confirmation_token in confirm_url
    assert mailer.existing_user_invites == []


async def test_create_invite_reuses_pending_row_when_re_inviting_same_email():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    entity_a = Entity(id="e1", world_id=WORLD_ID, name="Entity A")
    entity_b = Entity(id="e2", world_id=WORLD_ID, name="Entity B")
    entities = FakeEntityRepository(entities_by_id={entity_a.id: entity_a, entity_b.id: entity_b})
    invites = FakeInviteRepository()
    repos = Repositories(
        users=FakeUserRepository(),
        worlds=FakeWorldRepository(worlds_by_id={world.id: world}),
        entities=entities,
        permissions=FakePermissionRepository(),
        invites=invites,
        sessions=FakeSessionRepository(),
        password_resets=FakePasswordResetRepository(),
        pending_registrations=FakePendingRegistrationRepository(),
    )
    mailer = FakeMailer()

    grant_a = InviteGrant(entity_id="e1", level=PermissionLevel.READ)
    grant_b = InviteGrant(entity_id="e2", level=PermissionLevel.WRITE)
    first = await create_invite(repos, mailer, OWNER_ID, WORLD_ID, "missing@example.com", grant_a)
    second = await create_invite(repos, mailer, OWNER_ID, WORLD_ID, "missing@example.com", grant_b)

    assert len(invites.invites) == 1
    assert second.id == first.id
    assert second.entity_id == "e2"
    assert second.level == PermissionLevel.WRITE


async def test_create_invite_raises_when_entity_not_found():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world, users={GRANTEE_ID: make_invitee()})
    mailer = FakeMailer()
    grant = InviteGrant(entity_id=ENTITY_ID, level=PermissionLevel.READ)

    with pytest.raises(EntityNotFoundError):
        await create_invite(repos, mailer, OWNER_ID, WORLD_ID, "grantee@example.com", grant)


async def test_create_invite_raises_when_caller_is_not_owner():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world)
    mailer = FakeMailer()
    grant = InviteGrant(entity_id=ENTITY_ID, level=PermissionLevel.READ)

    with pytest.raises(PermissionDeniedError):
        await create_invite(repos, mailer, OTHER_USER_ID, WORLD_ID, "grantee@example.com", grant)


async def test_list_invites_for_world_returns_all_invites_including_accepted():
    pending = WorldInvite(
        id="i1",
        world_id=WORLD_ID,
        invitee_id=None,
        invitee_email="a@example.com",
        entity_id=ENTITY_ID,
        level=PermissionLevel.READ,
        accepted=False,
    )
    accepted = WorldInvite(
        id="i2",
        world_id=WORLD_ID,
        invitee_id=GRANTEE_ID,
        invitee_email="b@example.com",
        entity_id=ENTITY_ID,
        level=PermissionLevel.WRITE,
        accepted=True,
    )
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world, invites=FakeInviteRepository(invites=[pending, accepted]))

    result = await list_invites_for_world(repos, OWNER_ID, WORLD_ID)

    assert {invite.id for invite in result} == {pending.id, accepted.id}


async def test_list_invites_for_world_raises_when_caller_is_not_owner():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world)

    with pytest.raises(PermissionDeniedError):
        await list_invites_for_world(repos, OTHER_USER_ID, WORLD_ID)


async def test_accept_invite_succeeds_for_the_invitee():
    invites = FakeInviteRepository()
    repos = Repositories(
        users=FakeUserRepository(),
        worlds=FakeWorldRepository(),
        entities=FakeEntityRepository(),
        permissions=FakePermissionRepository(),
        invites=invites,
        sessions=FakeSessionRepository(),
        password_resets=FakePasswordResetRepository(),
        pending_registrations=FakePendingRegistrationRepository(),
    )
    invite = WorldInvite(
        id="i1",
        world_id=WORLD_ID,
        invitee_id=GRANTEE_ID,
        invitee_email="grantee@example.com",
        entity_id=ENTITY_ID,
        level=PermissionLevel.READ,
    )

    await accept_invite(repos, GRANTEE_ID, invite)

    assert invite in invites.invites


async def test_accept_invite_raises_when_caller_is_not_the_invitee():
    repos = make_repos()
    invite = WorldInvite(
        id="i1",
        world_id=WORLD_ID,
        invitee_id=GRANTEE_ID,
        invitee_email="grantee@example.com",
        entity_id=ENTITY_ID,
        level=PermissionLevel.READ,
    )

    with pytest.raises(PermissionDeniedError):
        await accept_invite(repos, OTHER_USER_ID, invite)


async def test_list_pending_invites_returns_only_the_callers_pending_invites():
    invites = FakeInviteRepository(
        invites=[
            WorldInvite(
                id="i1",
                world_id=WORLD_ID,
                invitee_id=GRANTEE_ID,
                invitee_email="grantee@example.com",
                entity_id=ENTITY_ID,
                level=PermissionLevel.READ,
            ),
            WorldInvite(
                id="i2",
                world_id="w2",
                invitee_id=OTHER_USER_ID,
                invitee_email="other@example.com",
                entity_id="e2",
                level=PermissionLevel.WRITE,
            ),
        ]
    )
    repos = Repositories(
        users=FakeUserRepository(),
        worlds=FakeWorldRepository(),
        entities=FakeEntityRepository(),
        permissions=FakePermissionRepository(),
        invites=invites,
        sessions=FakeSessionRepository(),
        password_resets=FakePasswordResetRepository(),
        pending_registrations=FakePendingRegistrationRepository(),
    )

    result = await list_pending_invites(repos, GRANTEE_ID)

    assert [invite.world_id for invite in result] == [WORLD_ID]


async def test_accept_invite_for_world_accepts_the_matching_pending_invite():
    invites = FakeInviteRepository(
        invites=[
            WorldInvite(
                id="i1",
                world_id=WORLD_ID,
                invitee_id=GRANTEE_ID,
                invitee_email="grantee@example.com",
                entity_id=ENTITY_ID,
                level=PermissionLevel.READ,
            )
        ]
    )
    repos = Repositories(
        users=FakeUserRepository(),
        worlds=FakeWorldRepository(),
        entities=FakeEntityRepository(),
        permissions=FakePermissionRepository(),
        invites=invites,
        sessions=FakeSessionRepository(),
        password_resets=FakePasswordResetRepository(),
        pending_registrations=FakePendingRegistrationRepository(),
    )

    await accept_invite_for_world(repos, GRANTEE_ID, WORLD_ID)

    accepted_invite = WorldInvite(
        id="i1",
        world_id=WORLD_ID,
        invitee_id=GRANTEE_ID,
        invitee_email="grantee@example.com",
        entity_id=ENTITY_ID,
        level=PermissionLevel.READ,
    )
    assert accepted_invite in invites.invites


async def test_accept_invite_for_world_raises_when_no_pending_invite_matches():
    repos = make_repos()

    with pytest.raises(InviteNotFoundError):
        await accept_invite_for_world(repos, GRANTEE_ID, WORLD_ID)
