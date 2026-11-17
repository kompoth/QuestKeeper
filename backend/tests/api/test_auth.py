from app.adapters.db.orm import UserRow
from app.domain.models import UserRole
from app.domain.security import hash_password

EMAIL = "user@example.com"
PASSWORD = "correct horse battery staple"  # noqa: S105


async def _create_user(db_session, user_id="u1", *, role=UserRole.MEMBER, email=EMAIL) -> None:
    db_session.add(UserRow(id=user_id, name="User", email=email, hashed_password=hash_password(PASSWORD), role=role))
    await db_session.commit()


def _csrf_headers(async_client) -> dict[str, str]:
    return {"X-CSRF-Token": async_client.cookies["csrf_token"]}


async def test_login_sets_session_and_csrf_cookies_and_returns_the_user(async_client, db_session):
    await _create_user(db_session)

    response = await async_client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})

    assert response.status_code == 200
    assert response.json()["email"] == EMAIL
    assert "hashed_password" not in response.json()
    assert async_client.cookies.get("session") is not None
    assert async_client.cookies.get("csrf_token") is not None


async def test_login_fails_with_wrong_password(async_client, db_session):
    await _create_user(db_session)

    response = await async_client.post("/auth/login", json={"email": EMAIL, "password": "wrong"})

    assert response.status_code == 401


async def test_me_requires_a_session(async_client):
    response = await async_client.get("/auth/me")

    assert response.status_code == 401


async def test_me_returns_the_logged_in_user(async_client, db_session):
    await _create_user(db_session)
    await async_client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})

    response = await async_client.get("/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == EMAIL


async def test_logout_requires_csrf_header(async_client, db_session):
    await _create_user(db_session)
    await async_client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})

    response = await async_client.post("/auth/logout")

    assert response.status_code == 403


async def test_logout_clears_the_session(async_client, db_session):
    await _create_user(db_session)
    await async_client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    csrf_token = async_client.cookies["csrf_token"]

    response = await async_client.post("/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert response.status_code == 200

    me_response = await async_client.get("/auth/me")
    assert me_response.status_code == 401


async def test_password_recovery_sends_mail_for_known_email(async_client, db_session, mailer):
    await _create_user(db_session)

    response = await async_client.post("/auth/password-recovery", json={"email": EMAIL})

    assert response.status_code == 200
    assert len(mailer.password_resets) == 1
    assert mailer.password_resets[0][0] == EMAIL


async def test_password_recovery_responds_the_same_way_for_unknown_email(async_client, mailer):
    response = await async_client.post("/auth/password-recovery", json={"email": "unknown@example.com"})

    assert response.status_code == 200
    assert mailer.password_resets == []


async def test_password_reset_updates_password_and_revokes_other_sessions(async_client, db_session, mailer):
    await _create_user(db_session)
    await async_client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    old_session_cookie = async_client.cookies["session"]

    await async_client.post("/auth/password-recovery", json={"email": EMAIL})
    reset_url = mailer.password_resets[0][1]
    token = reset_url.split("token=")[1]

    response = await async_client.post("/auth/password-reset", json={"token": token, "new_password": "new password"})
    assert response.status_code == 200

    async_client.cookies.set("session", old_session_cookie)
    me_response = await async_client.get("/auth/me")
    assert me_response.status_code == 401

    login_response = await async_client.post("/auth/login", json={"email": EMAIL, "password": "new password"})
    assert login_response.status_code == 200


async def test_password_reset_rejects_unknown_or_expired_token(async_client):
    response = await async_client.post(
        "/auth/password-reset", json={"token": "missing-token", "new_password": "new password"}
    )

    assert response.status_code == 404


async def test_register_then_confirm_logs_in_the_new_user(async_client, mailer):
    register_response = await async_client.post(
        "/auth/register", json={"name": "New User", "email": "newbie@example.com", "password": PASSWORD}
    )
    assert register_response.status_code == 200
    assert len(mailer.registration_confirmations) == 1
    _, confirm_url = mailer.registration_confirmations[0]
    token = confirm_url.split("token=")[1]

    confirm_response = await async_client.post("/auth/register/confirm", json={"token": token})
    assert confirm_response.status_code == 200
    assert confirm_response.json()["email"] == "newbie@example.com"
    assert async_client.cookies.get("session") is not None

    me_response = await async_client.get("/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "newbie@example.com"


async def test_registration_disabled_blocks_register_but_not_invite_confirm(
    async_client, db_session, mailer, monkeypatch
):
    await _create_user(db_session, user_id="owner")
    await async_client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    world_response = await async_client.post("/worlds", json={"name": "World"}, headers=_csrf_headers(async_client))
    world_id = world_response.json()["id"]
    entity_response = await async_client.post(
        f"/worlds/{world_id}/entities", json={"name": "Root"}, headers=_csrf_headers(async_client)
    )
    entity_id = entity_response.json()["id"]
    await async_client.post(
        f"/worlds/{world_id}/invites",
        json={"invitee_email": "stranger@example.com", "entity_id": entity_id, "level": "read"},
        headers=_csrf_headers(async_client),
    )
    _, _, invite_confirm_url = mailer.new_user_invites[-1]
    invite_token = invite_confirm_url.split("token=")[1]

    monkeypatch.setenv("REGISTRATION_ENABLED", "false")

    register_response = await async_client.post(
        "/auth/register", json={"name": "New User", "email": "newbie@example.com", "password": PASSWORD}
    )
    assert register_response.status_code == 403

    invite_confirm_response = await async_client.post(
        "/invites/confirm", json={"token": invite_token, "name": "Stranger", "password": PASSWORD}
    )
    assert invite_confirm_response.status_code == 200


async def test_password_reset_disabled_blocks_public_routes_but_admin_override_still_works(
    async_client, db_session, mailer, monkeypatch
):
    await _create_user(db_session, user_id="target")
    await _create_user(db_session, user_id="admin", role=UserRole.ADMIN, email="admin@example.com")
    await async_client.post("/auth/login", json={"email": "admin@example.com", "password": PASSWORD})

    monkeypatch.setenv("PASSWORD_RESET_ENABLED", "false")

    recovery_response = await async_client.post("/auth/password-recovery", json={"email": EMAIL})
    assert recovery_response.status_code == 403

    admin_response = await async_client.post("/auth/admin/password-reset/target", headers=_csrf_headers(async_client))
    assert admin_response.status_code == 200
    assert mailer.password_resets[-1][0] == EMAIL


async def test_admin_password_reset_requires_admin_role(async_client, db_session):
    await _create_user(db_session, user_id="target")
    await _create_user(db_session, user_id="other", role=UserRole.MEMBER, email="other@example.com")
    await async_client.post("/auth/login", json={"email": "other@example.com", "password": PASSWORD})

    response = await async_client.post("/auth/admin/password-reset/target", headers=_csrf_headers(async_client))

    assert response.status_code == 403


async def test_admin_password_reset_returns_404_for_unknown_user(async_client, db_session):
    await _create_user(db_session, user_id="admin", role=UserRole.ADMIN, email="admin@example.com")
    await async_client.post("/auth/login", json={"email": "admin@example.com", "password": PASSWORD})

    response = await async_client.post("/auth/admin/password-reset/missing", headers=_csrf_headers(async_client))

    assert response.status_code == 404
