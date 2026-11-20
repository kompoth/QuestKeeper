import pytest

from app.adapters.db.orm import UserRow
from app.domain.models import UserRole
from app.domain.security import hash_password

pytestmark = pytest.mark.asyncio(loop_scope="session")

EMAIL = "user@example.com"
PASSWORD = "correct horse battery staple"  # noqa: S105


async def _login(async_client, db_session, *, email=EMAIL, user_id="owner") -> None:
    db_session.add(
        UserRow(id=user_id, name="User", email=email, hashed_password=hash_password(PASSWORD), role=UserRole.MEMBER)
    )
    await db_session.commit()
    await async_client.post("/auth/login", json={"email": email, "password": PASSWORD})


def _csrf_headers(async_client) -> dict[str, str]:
    return {"X-CSRF-Token": async_client.cookies["csrf_token"]}


async def _create_world(async_client) -> str:
    response = await async_client.post("/worlds", json={"name": "World"}, headers=_csrf_headers(async_client))
    return response.json()["id"]


async def _create_entity(async_client, world_id: str, name: str = "Root") -> str:
    response = await async_client.post(
        f"/worlds/{world_id}/entities", json={"name": name}, headers=_csrf_headers(async_client)
    )
    return response.json()["id"]


async def test_grant_permission_requires_ownership(async_client, db_session):
    await _login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)
    entity_id = await _create_entity(async_client, world_id)
    await _login(async_client, db_session, email="other@example.com", user_id="other")

    response = await async_client.post(
        f"/worlds/{world_id}/permissions",
        json={"grantee_email": "other@example.com", "entity_id": entity_id, "level": "write"},
        headers=_csrf_headers(async_client),
    )

    assert response.status_code == 403


async def test_grant_and_revoke_permission(async_client, db_session):
    await _login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)
    entity_id = await _create_entity(async_client, world_id)
    db_session.add(
        UserRow(id="grantee", name="Grantee", email="grantee@example.com", hashed_password="x", role=UserRole.MEMBER)
    )
    await db_session.commit()
    await async_client.post(
        f"/worlds/{world_id}/invites",
        json={"invitee_email": "grantee@example.com"},
        headers=_csrf_headers(async_client),
    )

    grant_response = await async_client.post(
        f"/worlds/{world_id}/permissions",
        json={"grantee_email": "grantee@example.com", "entity_id": entity_id, "level": "write"},
        headers=_csrf_headers(async_client),
    )
    assert grant_response.status_code == 200

    permissions_response = await async_client.get(f"/worlds/{world_id}/entities/{entity_id}/permissions")
    assert permissions_response.status_code == 200
    assert permissions_response.json() == {
        "direct": [{"user_id": "grantee", "email": "grantee@example.com", "name": None, "level": "write"}],
        "inherited": [],
    }

    revoke_response = await async_client.delete(
        f"/worlds/{world_id}/permissions/grantee/{entity_id}", headers=_csrf_headers(async_client)
    )
    assert revoke_response.status_code == 204

    permissions_after_revoke = await async_client.get(f"/worlds/{world_id}/entities/{entity_id}/permissions")
    assert permissions_after_revoke.json() == {"direct": [], "inherited": []}


async def test_get_permissions_reports_null_name_for_a_grantee_with_an_unaccepted_invite(async_client, db_session):
    """A grantee's name must stay hidden while they have a not-yet-accepted invite to this world -
    revealing it earlier would leak that the email belongs to a known account before they accept."""
    await _login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)
    entity_id = await _create_entity(async_client, world_id)
    db_session.add(
        UserRow(id="grantee", name="Grantee", email="grantee@example.com", hashed_password="x", role=UserRole.MEMBER)
    )
    await db_session.commit()

    await async_client.post(
        f"/worlds/{world_id}/invites",
        json={"invitee_email": "grantee@example.com"},
        headers=_csrf_headers(async_client),
    )
    await async_client.post(
        f"/worlds/{world_id}/permissions",
        json={"grantee_email": "grantee@example.com", "entity_id": entity_id, "level": "write"},
        headers=_csrf_headers(async_client),
    )

    permissions_response = await async_client.get(f"/worlds/{world_id}/entities/{entity_id}/permissions")
    assert permissions_response.status_code == 200
    [grant] = permissions_response.json()["direct"]
    assert grant["email"] == "grantee@example.com"
    assert grant["name"] is None


async def test_get_permissions_reports_name_once_the_grantees_invite_is_accepted(async_client, db_session):
    await _login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)
    entity_id = await _create_entity(async_client, world_id)
    db_session.add(
        UserRow(
            id="grantee",
            name="Grantee",
            email="grantee@example.com",
            hashed_password=hash_password(PASSWORD),
            role=UserRole.MEMBER,
        )
    )
    await db_session.commit()

    await async_client.post(
        f"/worlds/{world_id}/invites",
        json={"invitee_email": "grantee@example.com"},
        headers=_csrf_headers(async_client),
    )
    await async_client.post(
        f"/worlds/{world_id}/permissions",
        json={"grantee_email": "grantee@example.com", "entity_id": entity_id, "level": "write"},
        headers=_csrf_headers(async_client),
    )

    await async_client.post("/auth/login", json={"email": "grantee@example.com", "password": PASSWORD})
    await async_client.post(f"/invites/{world_id}/accept", headers=_csrf_headers(async_client))

    await async_client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    permissions_response = await async_client.get(f"/worlds/{world_id}/entities/{entity_id}/permissions")
    [grant] = permissions_response.json()["direct"]
    assert grant["name"] == "Grantee"


async def test_grant_permission_raises_404_for_a_grantee_with_no_invite_at_all(async_client, db_session):
    """Entity access can only ever be granted to someone already invited to the world - an invite
    is what unlocks the world itself; granting narrows what they can see or edit inside it."""
    await _login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)
    entity_id = await _create_entity(async_client, world_id)
    db_session.add(
        UserRow(id="grantee", name="Grantee", email="grantee@example.com", hashed_password="x", role=UserRole.MEMBER)
    )
    await db_session.commit()

    grant_response = await async_client.post(
        f"/worlds/{world_id}/permissions",
        json={"grantee_email": "grantee@example.com", "entity_id": entity_id, "level": "write"},
        headers=_csrf_headers(async_client),
    )

    assert grant_response.status_code == 404


async def test_create_invite_and_list_and_accept(async_client, db_session):
    await _login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)
    db_session.add(
        UserRow(
            id="invitee",
            name="Invitee",
            email="invitee@example.com",
            hashed_password=hash_password(PASSWORD),
            role=UserRole.MEMBER,
        )
    )
    await db_session.commit()

    invite_response = await async_client.post(
        f"/worlds/{world_id}/invites",
        json={"invitee_email": "invitee@example.com"},
        headers=_csrf_headers(async_client),
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

    accept_response = await async_client.post(f"/invites/{world_id}/accept", headers=_csrf_headers(async_client))
    assert accept_response.status_code == 200

    await async_client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    post_accept_response = await async_client.get(f"/worlds/{world_id}/invites")
    assert post_accept_response.status_code == 200
    assert post_accept_response.json() == [
        {"invitee_email": "invitee@example.com", "invitee_name": "Invitee", "accepted": True},
    ]


async def test_list_invites_reports_null_name_for_a_still_unregistered_invitee(async_client, db_session):
    await _login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)

    await async_client.post(
        f"/worlds/{world_id}/invites",
        json={"invitee_email": "stranger@example.com"},
        headers=_csrf_headers(async_client),
    )

    list_response = await async_client.get(f"/worlds/{world_id}/invites")
    assert list_response.status_code == 200
    [invite] = list_response.json()
    assert invite["invitee_email"] == "stranger@example.com"
    assert invite["invitee_name"] is None


async def test_list_invites_reports_null_name_for_a_registered_but_unaccepted_invitee(async_client, db_session):
    """A pre-existing account's real name must stay hidden until they themselves accept - otherwise
    the owner could tell whether an invited email already has an account before acceptance."""
    await _login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)
    db_session.add(
        UserRow(
            id="invitee",
            name="Invitee",
            email="invitee@example.com",
            hashed_password=hash_password(PASSWORD),
            role=UserRole.MEMBER,
        )
    )
    await db_session.commit()

    await async_client.post(
        f"/worlds/{world_id}/invites",
        json={"invitee_email": "invitee@example.com"},
        headers=_csrf_headers(async_client),
    )

    list_response = await async_client.get(f"/worlds/{world_id}/invites")
    assert list_response.status_code == 200
    [invite] = list_response.json()
    assert invite["invitee_email"] == "invitee@example.com"
    assert invite["invitee_name"] is None
    assert invite["accepted"] is False


async def test_expel_invitee_deletes_a_pending_invite(async_client, db_session):
    await _login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)
    db_session.add(
        UserRow(
            id="invitee",
            name="Invitee",
            email="invitee@example.com",
            hashed_password=hash_password(PASSWORD),
            role=UserRole.MEMBER,
        )
    )
    await db_session.commit()

    await async_client.post(
        f"/worlds/{world_id}/invites",
        json={"invitee_email": "invitee@example.com"},
        headers=_csrf_headers(async_client),
    )

    expel_response = await async_client.request(
        "DELETE",
        f"/worlds/{world_id}/invites",
        params={"email": "invitee@example.com"},
        headers=_csrf_headers(async_client),
    )
    assert expel_response.status_code == 204

    list_response = await async_client.get(f"/worlds/{world_id}/invites")
    assert list_response.json() == []


async def test_expel_invitee_deletes_an_accepted_invite(async_client, db_session):
    await _login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)
    db_session.add(
        UserRow(
            id="invitee",
            name="Invitee",
            email="invitee@example.com",
            hashed_password=hash_password(PASSWORD),
            role=UserRole.MEMBER,
        )
    )
    await db_session.commit()

    await async_client.post(
        f"/worlds/{world_id}/invites",
        json={"invitee_email": "invitee@example.com"},
        headers=_csrf_headers(async_client),
    )

    await async_client.post("/auth/login", json={"email": "invitee@example.com", "password": PASSWORD})
    await async_client.post(f"/invites/{world_id}/accept", headers=_csrf_headers(async_client))

    await async_client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    expel_response = await async_client.request(
        "DELETE",
        f"/worlds/{world_id}/invites",
        params={"email": "invitee@example.com"},
        headers=_csrf_headers(async_client),
    )
    assert expel_response.status_code == 204

    list_response = await async_client.get(f"/worlds/{world_id}/invites")
    assert list_response.json() == []


async def test_expel_invitee_raises_404_when_no_invite_exists(async_client, db_session):
    await _login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)

    response = await async_client.request(
        "DELETE",
        f"/worlds/{world_id}/invites",
        params={"email": "nobody@example.com"},
        headers=_csrf_headers(async_client),
    )
    assert response.status_code == 404


async def test_expel_invitee_requires_ownership(async_client, db_session):
    await _login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)
    await _login(async_client, db_session, email="other@example.com", user_id="other")

    response = await async_client.request(
        "DELETE",
        f"/worlds/{world_id}/invites",
        params={"email": "nobody@example.com"},
        headers=_csrf_headers(async_client),
    )
    assert response.status_code == 403


async def test_accept_invite_raises_404_when_no_pending_invite_matches(async_client, db_session):
    await _login(async_client, db_session, user_id="u1")

    response = await async_client.post("/invites/missing-world/accept", headers=_csrf_headers(async_client))

    assert response.status_code == 404


async def test_create_invite_for_unknown_email_sends_signup_link_and_new_user_can_confirm(
    async_client, db_session, mailer
):
    await _login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)

    invite_response = await async_client.post(
        f"/worlds/{world_id}/invites",
        json={"invitee_email": "stranger@example.com"},
        headers=_csrf_headers(async_client),
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
    await _login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)
    db_session.add(
        UserRow(id="invitee", name="Invitee", email="invitee@example.com", hashed_password="x", role=UserRole.MEMBER)
    )
    await db_session.commit()

    await async_client.post(
        f"/worlds/{world_id}/invites",
        json={"invitee_email": "invitee@example.com"},
        headers=_csrf_headers(async_client),
    )
    await async_client.post(
        f"/worlds/{world_id}/invites",
        json={"invitee_email": "stranger@example.com"},
        headers=_csrf_headers(async_client),
    )

    response = await async_client.get(f"/worlds/{world_id}/invites")

    assert response.status_code == 200
    invites = response.json()
    assert len(invites) == 2
    for invite in invites:
        assert set(invite.keys()) == {"invitee_email", "invitee_name", "accepted"}


async def test_list_invites_for_world_requires_ownership(async_client, db_session):
    await _login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)
    await _login(async_client, db_session, email="other@example.com", user_id="other")

    response = await async_client.get(f"/worlds/{world_id}/invites")

    assert response.status_code == 403


async def test_confirm_invite_rejects_unknown_or_expired_token(async_client):
    response = await async_client.post(
        "/invites/confirm", json={"token": "missing-token", "name": "Nobody", "password": PASSWORD}
    )

    assert response.status_code == 404


async def test_confirm_invite_rejects_when_email_already_activated_in_the_meantime(async_client, db_session, mailer):
    await _login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)

    await async_client.post(
        f"/worlds/{world_id}/invites",
        json={"invitee_email": "late-signup@example.com"},
        headers=_csrf_headers(async_client),
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
