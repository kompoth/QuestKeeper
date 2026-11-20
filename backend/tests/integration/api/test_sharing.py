import pytest

from app.adapters.db.orm import UserRow
from app.domain.models import UserRole
from app.domain.security import hash_password
from tests.integration.api.conftest import EMAIL, PASSWORD, csrf_headers, login

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _create_world(async_client) -> str:
    response = await async_client.post("/worlds", json={"name": "World"}, headers=csrf_headers(async_client))
    return response.json()["id"]


async def _create_entity(async_client, world_id: str, name: str = "Root") -> str:
    response = await async_client.post(
        f"/worlds/{world_id}/entities", json={"name": name}, headers=csrf_headers(async_client)
    )
    return response.json()["id"]


async def _register_user(db_session, user_id: str, email: str, name: str, *, loginable: bool = False) -> None:
    """Adds a user row. `loginable` uses the shared PASSWORD hash, for tests that later log in as them."""
    hashed = hash_password(PASSWORD) if loginable else "x"
    db_session.add(UserRow(id=user_id, name=name, email=email, hashed_password=hashed, role=UserRole.MEMBER))
    await db_session.commit()


async def test_grant_and_revoke_permission(async_client, db_session):
    await login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)
    entity_id = await _create_entity(async_client, world_id)
    await _register_user(db_session, "grantee", "grantee@example.com", "Grantee")
    await async_client.post(
        f"/worlds/{world_id}/invites",
        json={"invitee_email": "grantee@example.com"},
        headers=csrf_headers(async_client),
    )

    grant_response = await async_client.post(
        f"/worlds/{world_id}/permissions",
        json={"grantee_email": "grantee@example.com", "entity_id": entity_id, "level": "write"},
        headers=csrf_headers(async_client),
    )
    assert grant_response.status_code == 200

    permissions_response = await async_client.get(f"/worlds/{world_id}/entities/{entity_id}/permissions")
    assert permissions_response.status_code == 200
    assert permissions_response.json() == {
        "direct": [{"user_id": "grantee", "email": "grantee@example.com", "name": None, "level": "write"}],
        "inherited": [],
    }

    revoke_response = await async_client.delete(
        f"/worlds/{world_id}/permissions/grantee/{entity_id}", headers=csrf_headers(async_client)
    )
    assert revoke_response.status_code == 204

    permissions_after_revoke = await async_client.get(f"/worlds/{world_id}/entities/{entity_id}/permissions")
    assert permissions_after_revoke.json() == {"direct": [], "inherited": []}


async def test_get_permissions_reports_null_name_for_a_grantee_with_an_unaccepted_invite(async_client, db_session):
    """A grantee's name must stay hidden while they have a not-yet-accepted invite to this world -
    revealing it earlier would leak that the email belongs to a known account before they accept."""
    await login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)
    entity_id = await _create_entity(async_client, world_id)
    await _register_user(db_session, "grantee", "grantee@example.com", "Grantee")

    await async_client.post(
        f"/worlds/{world_id}/invites",
        json={"invitee_email": "grantee@example.com"},
        headers=csrf_headers(async_client),
    )
    await async_client.post(
        f"/worlds/{world_id}/permissions",
        json={"grantee_email": "grantee@example.com", "entity_id": entity_id, "level": "write"},
        headers=csrf_headers(async_client),
    )

    permissions_response = await async_client.get(f"/worlds/{world_id}/entities/{entity_id}/permissions")
    assert permissions_response.status_code == 200
    [grant] = permissions_response.json()["direct"]
    assert grant["email"] == "grantee@example.com"
    assert grant["name"] is None


async def test_get_permissions_reports_name_once_the_grantees_invite_is_accepted(async_client, db_session):
    await login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)
    entity_id = await _create_entity(async_client, world_id)
    await _register_user(db_session, "grantee", "grantee@example.com", "Grantee", loginable=True)

    await async_client.post(
        f"/worlds/{world_id}/invites",
        json={"invitee_email": "grantee@example.com"},
        headers=csrf_headers(async_client),
    )
    await async_client.post(
        f"/worlds/{world_id}/permissions",
        json={"grantee_email": "grantee@example.com", "entity_id": entity_id, "level": "write"},
        headers=csrf_headers(async_client),
    )

    await async_client.post("/auth/login", json={"email": "grantee@example.com", "password": PASSWORD})
    await async_client.post(f"/invites/{world_id}/accept", headers=csrf_headers(async_client))

    await async_client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    permissions_response = await async_client.get(f"/worlds/{world_id}/entities/{entity_id}/permissions")
    [grant] = permissions_response.json()["direct"]
    assert grant["name"] == "Grantee"


async def test_create_invite_and_list_and_accept(async_client, db_session):
    await login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)
    await _register_user(db_session, "invitee", "invitee@example.com", "Invitee", loginable=True)

    invite_response = await async_client.post(
        f"/worlds/{world_id}/invites",
        json={"invitee_email": "invitee@example.com"},
        headers=csrf_headers(async_client),
    )
    assert invite_response.status_code == 200
    assert "invitee_id" not in invite_response.json()
    assert invite_response.json() == {
        "invitee_email": "invitee@example.com",
        "invitee_name": None,
        "accepted": False,
    }

    await async_client.post("/auth/login", json={"email": "invitee@example.com", "password": PASSWORD})

    list_response = await async_client.get("/invites")
    assert list_response.status_code == 200
    assert [invite["world_id"] for invite in list_response.json()] == [world_id]
    assert "invitee_id" not in list_response.json()[0]

    accept_response = await async_client.post(f"/invites/{world_id}/accept", headers=csrf_headers(async_client))
    assert accept_response.status_code == 200

    await async_client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    post_accept_response = await async_client.get(f"/worlds/{world_id}/invites")
    assert post_accept_response.status_code == 200
    assert post_accept_response.json() == [
        {"invitee_email": "invitee@example.com", "invitee_name": "Invitee", "accepted": True},
    ]


async def test_create_invite_for_unknown_email_sends_signup_link_and_new_user_can_confirm(
    async_client, db_session, mailer
):
    await login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)

    invite_response = await async_client.post(
        f"/worlds/{world_id}/invites",
        json={"invitee_email": "stranger@example.com"},
        headers=csrf_headers(async_client),
    )
    assert invite_response.status_code == 200
    assert invite_response.json()["accepted"] is False

    assert len(mailer.new_user_invites) == 1
    to_email, _world_name, confirm_url = mailer.new_user_invites[0]
    assert to_email == "stranger@example.com"
    token = confirm_url.split("token=")[1]

    confirm_response = await async_client.post(
        "/invites/confirm", json={"token": token, "name": "Stranger", "password": PASSWORD}
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["email"] == "stranger@example.com"

    me_response = await async_client.get("/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "stranger@example.com"


async def test_owner_lists_all_invites_for_world_without_leaking_invitee_id(async_client, db_session):
    await login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)
    await _register_user(db_session, "invitee", "invitee@example.com", "Invitee")

    await async_client.post(
        f"/worlds/{world_id}/invites",
        json={"invitee_email": "invitee@example.com"},
        headers=csrf_headers(async_client),
    )
    await async_client.post(
        f"/worlds/{world_id}/invites",
        json={"invitee_email": "stranger@example.com"},
        headers=csrf_headers(async_client),
    )

    response = await async_client.get(f"/worlds/{world_id}/invites")

    assert response.status_code == 200
    invites = response.json()
    assert len(invites) == 2
    for invite in invites:
        assert set(invite.keys()) == {"invitee_email", "invitee_name", "accepted"}


async def test_confirm_invite_rejects_when_email_already_activated_in_the_meantime(async_client, db_session, mailer):
    await login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)

    await async_client.post(
        f"/worlds/{world_id}/invites",
        json={"invitee_email": "late-signup@example.com"},
        headers=csrf_headers(async_client),
    )
    _, _, invite_confirm_url = mailer.new_user_invites[-1]
    invite_token = invite_confirm_url.split("token=")[1]

    # The same (already-pending) email self-registers and confirms before the invite is used.
    await async_client.post(
        "/auth/register", json={"name": "Late Signup", "email": "late-signup@example.com", "password": PASSWORD}
    )
    _, registration_confirm_url = mailer.registration_confirmations[-1]
    registration_token = registration_confirm_url.split("token=")[1]
    await async_client.post("/auth/register/confirm", json={"token": registration_token})

    response = await async_client.post(
        "/invites/confirm", json={"token": invite_token, "name": "Late Signup", "password": PASSWORD}
    )

    assert response.status_code == 409
