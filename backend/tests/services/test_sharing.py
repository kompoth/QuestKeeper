import pytest

from app.domain.models import Entity, EntityPermission, PermissionLevel, User, UserRole, World, WorldInvite
from app.domain.repositories import Repositories
from app.services.access import EntityNotFoundError, PermissionDeniedError, UserNotFoundError, WorldNotFoundError
from app.services.sharing import InviteGrant, accept_invite, create_invite, grant_permission, revoke_permission
from tests.services.fakes import (
    FakeEntityRepository,
    FakeInviteRepository,
    FakePermissionRepository,
    FakeUserRepository,
    FakeWorldRepository,
)

WORLD_ID = "w1"
OWNER_ID = "owner"
OTHER_USER_ID = "other"
GRANTEE_ID = "grantee"
ENTITY_ID = "e1"


def make_repos(*, world=None, entity=None, users=None) -> Repositories:
    return Repositories(
        users=FakeUserRepository(users_by_id=users or {}),
        worlds=FakeWorldRepository(worlds_by_id={world.id: world} if world else {}),
        entities=FakeEntityRepository(entities_by_id={entity.id: entity} if entity else {}),
        permissions=FakePermissionRepository(),
        invites=FakeInviteRepository(),
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


async def test_create_invite_succeeds_for_world_owner():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity")
    repos = make_repos(world=world, entity=entity, users={GRANTEE_ID: make_invitee()})
    grant = InviteGrant(entity_id=ENTITY_ID, level=PermissionLevel.READ)

    invite = await create_invite(repos, OWNER_ID, WORLD_ID, "grantee@example.com", grant)

    expected = WorldInvite(world_id=WORLD_ID, invitee_id=GRANTEE_ID, entity_id=ENTITY_ID, level=PermissionLevel.READ)
    assert invite == expected
    pending = await repos.invites.get_pending_for_user(GRANTEE_ID)
    assert invite in pending


async def test_create_invite_raises_when_invitee_email_unknown():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    entity = Entity(id=ENTITY_ID, world_id=WORLD_ID, name="Entity")
    repos = make_repos(world=world, entity=entity)
    grant = InviteGrant(entity_id=ENTITY_ID, level=PermissionLevel.READ)

    with pytest.raises(UserNotFoundError):
        await create_invite(repos, OWNER_ID, WORLD_ID, "missing@example.com", grant)


async def test_create_invite_raises_when_entity_not_found():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world, users={GRANTEE_ID: make_invitee()})
    grant = InviteGrant(entity_id=ENTITY_ID, level=PermissionLevel.READ)

    with pytest.raises(EntityNotFoundError):
        await create_invite(repos, OWNER_ID, WORLD_ID, "grantee@example.com", grant)


async def test_create_invite_raises_when_caller_is_not_owner():
    world = World(id=WORLD_ID, owner_id=OWNER_ID, name="World")
    repos = make_repos(world=world)
    grant = InviteGrant(entity_id=ENTITY_ID, level=PermissionLevel.READ)

    with pytest.raises(PermissionDeniedError):
        await create_invite(repos, OTHER_USER_ID, WORLD_ID, "grantee@example.com", grant)


async def test_accept_invite_succeeds_for_the_invitee():
    invites = FakeInviteRepository()
    repos = Repositories(
        users=FakeUserRepository(),
        worlds=FakeWorldRepository(),
        entities=FakeEntityRepository(),
        permissions=FakePermissionRepository(),
        invites=invites,
    )
    invite = WorldInvite(world_id=WORLD_ID, invitee_id=GRANTEE_ID, entity_id=ENTITY_ID, level=PermissionLevel.READ)

    await accept_invite(repos, GRANTEE_ID, invite)

    assert invite in invites.invites


async def test_accept_invite_raises_when_caller_is_not_the_invitee():
    repos = make_repos()
    invite = WorldInvite(world_id=WORLD_ID, invitee_id=GRANTEE_ID, entity_id=ENTITY_ID, level=PermissionLevel.READ)

    with pytest.raises(PermissionDeniedError):
        await accept_invite(repos, OTHER_USER_ID, invite)
