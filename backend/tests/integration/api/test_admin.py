import pytest

from app.adapters.db.orm import UserRow
from app.domain.models import UserRole
from app.domain.security import hash_password
from tests.integration.api.conftest import EMAIL, PASSWORD, csrf_headers

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _create_user(db_session, user_id="u1", *, role=UserRole.MEMBER, email=EMAIL) -> None:
    db_session.add(UserRow(id=user_id, name="User", email=email, hashed_password=hash_password(PASSWORD), role=role))
    await db_session.commit()


async def _login_as_admin(async_client, db_session, *, user_id="admin", email="admin@example.com") -> None:
    await _create_user(db_session, user_id=user_id, role=UserRole.ADMIN, email=email)
    await async_client.post("/auth/login", json={"email": email, "password": PASSWORD})


async def test_get_settings_requires_admin_role(async_client, db_session):
    await _create_user(db_session)
    await async_client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})

    response = await async_client.get("/admin/settings")

    assert response.status_code == 403


async def test_get_settings_returns_defaults_when_never_written(async_client, db_session):
    await _login_as_admin(async_client, db_session)

    response = await async_client.get("/admin/settings")

    assert response.status_code == 200
    assert response.json() == {"registration_enabled": True, "password_reset_enabled": True}


async def test_update_settings_round_trips(async_client, db_session):
    await _login_as_admin(async_client, db_session)

    update_response = await async_client.put(
        "/admin/settings",
        json={"registration_enabled": False, "password_reset_enabled": True},
        headers=csrf_headers(async_client),
    )
    assert update_response.status_code == 200
    assert update_response.json() == {"registration_enabled": False, "password_reset_enabled": True}

    get_response = await async_client.get("/admin/settings")
    assert get_response.json() == {"registration_enabled": False, "password_reset_enabled": True}


async def test_list_users_requires_admin_role(async_client, db_session):
    await _create_user(db_session)
    await async_client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})

    response = await async_client.get("/admin/users")

    assert response.status_code == 403


async def test_list_users_paginates(async_client, db_session):
    await _login_as_admin(async_client, db_session)
    await _create_user(db_session, user_id="u-a", email="a@example.com")
    await _create_user(db_session, user_id="u-b", email="b@example.com")

    response = await async_client.get("/admin/users", params={"offset": 0, "limit": 2})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert [user["email"] for user in body["users"]] == ["a@example.com", "admin@example.com"]


async def test_create_user_requires_admin_role(async_client, db_session):
    await _create_user(db_session)
    await async_client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})

    response = await async_client.post(
        "/admin/users",
        json={"name": "New User", "email": "newbie@example.com", "role": "member"},
        headers=csrf_headers(async_client),
    )

    assert response.status_code == 403


async def test_create_user_persists_the_account_and_sends_a_set_password_email(async_client, db_session, mailer):
    await _login_as_admin(async_client, db_session)

    response = await async_client.post(
        "/admin/users",
        json={"name": "New User", "email": "newbie@example.com", "role": "warden"},
        headers=csrf_headers(async_client),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "newbie@example.com"
    assert body["role"] == "warden"
    assert "hashed_password" not in body
    assert len(mailer.password_resets) == 1
    assert mailer.password_resets[0][0] == "newbie@example.com"

    list_response = await async_client.get("/admin/users")
    assert "newbie@example.com" in [user["email"] for user in list_response.json()["users"]]


async def test_create_user_returns_409_for_a_taken_email(async_client, db_session):
    await _login_as_admin(async_client, db_session)

    response = await async_client.post(
        "/admin/users",
        json={"name": "Dupe", "email": "admin@example.com", "role": "member"},
        headers=csrf_headers(async_client),
    )

    assert response.status_code == 409


async def test_banned_user_cannot_log_in(async_client, db_session):
    await _login_as_admin(async_client, db_session)
    await _create_user(db_session, user_id="target", email="target@example.com")

    await async_client.put("/admin/users/target/status", json={"status": "banned"}, headers=csrf_headers(async_client))

    response = await async_client.post("/auth/login", json={"email": "target@example.com", "password": PASSWORD})

    assert response.status_code == 403


async def test_banning_a_logged_in_user_invalidates_their_session(async_client, db_session):
    await _create_user(db_session, user_id="target", email="target@example.com")
    target_client_response = await async_client.post(
        "/auth/login", json={"email": "target@example.com", "password": PASSWORD}
    )
    assert target_client_response.status_code == 200
    target_cookies = dict(async_client.cookies)

    await _login_as_admin(async_client, db_session)
    await async_client.put("/admin/users/target/status", json={"status": "banned"}, headers=csrf_headers(async_client))

    async_client.cookies.clear()
    async_client.cookies.update(target_cookies)
    me_response = await async_client.get("/auth/me")

    assert me_response.status_code == 401
