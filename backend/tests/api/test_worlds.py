from datetime import UTC, datetime

from app.adapters.db.orm import EntityPermissionRow, EntityRow, UserRow, WorldRow
from app.domain.models import PermissionLevel, UserRole
from app.domain.security import hash_password

EMAIL = "user@example.com"
PASSWORD = "correct horse battery staple"  # noqa: S105


async def _login(async_client, db_session, user_id="u1") -> None:
    db_session.add(
        UserRow(id=user_id, name="User", email=EMAIL, hashed_password=hash_password(PASSWORD), role=UserRole.MEMBER)
    )
    await db_session.commit()
    await async_client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})


async def _create_owned_world(db_session, world_id="w1", owner_id="owner") -> None:
    db_session.add(
        UserRow(id=owner_id, name="Owner", email="owner@example.com", hashed_password="x", role=UserRole.MEMBER)
    )
    db_session.add(WorldRow(id=world_id, owner_id=owner_id, name="World"))
    await db_session.commit()


def _csrf_headers(async_client) -> dict[str, str]:
    return {"X-CSRF-Token": async_client.cookies["csrf_token"]}


async def test_list_my_worlds_requires_a_session(async_client):
    response = await async_client.get("/worlds")

    assert response.status_code == 401


async def test_create_world_requires_csrf_header(async_client, db_session):
    await _login(async_client, db_session)

    response = await async_client.post("/worlds", json={"name": "New World"})

    assert response.status_code == 403


async def test_create_and_list_worlds(async_client, db_session):
    await _login(async_client, db_session)

    create_response = await async_client.post(
        "/worlds", json={"name": "My World", "description": "A tale"}, headers=_csrf_headers(async_client)
    )
    assert create_response.status_code == 200
    assert create_response.json()["name"] == "My World"

    list_response = await async_client.get("/worlds")
    assert list_response.status_code == 200
    assert [world["name"] for world in list_response.json()] == ["My World"]


async def test_get_world_returns_404_when_not_found(async_client, db_session):
    await _login(async_client, db_session)

    response = await async_client.get("/worlds/missing")

    assert response.status_code == 404


async def test_get_world_returns_403_for_a_non_member(async_client, db_session):
    await _create_owned_world(db_session)
    await _login(async_client, db_session, user_id="u1")

    response = await async_client.get("/worlds/w1")

    assert response.status_code == 403


async def test_get_world_succeeds_for_a_user_with_any_grant(async_client, db_session):
    await _create_owned_world(db_session)
    await _login(async_client, db_session, user_id="u1")
    now = datetime.now(UTC)
    db_session.add(
        EntityRow(
            id="e1",
            world_id="w1",
            name="Entity",
            created_at=now,
            updated_at=now,
            created_by="owner",
            updated_by="owner",
        )
    )
    await db_session.commit()
    db_session.add(EntityPermissionRow(user_id="u1", entity_id="e1", level=PermissionLevel.READ))
    await db_session.commit()

    response = await async_client.get("/worlds/w1")

    assert response.status_code == 200
    assert response.json()["id"] == "w1"


async def test_update_world_requires_ownership(async_client, db_session):
    await _create_owned_world(db_session)
    await _login(async_client, db_session, user_id="u1")

    response = await async_client.patch("/worlds/w1", json={"name": "Renamed"}, headers=_csrf_headers(async_client))

    assert response.status_code == 403


async def test_update_world_succeeds_for_the_owner(async_client, db_session):
    await _login(async_client, db_session, user_id="owner")
    create_response = await async_client.post("/worlds", json={"name": "World"}, headers=_csrf_headers(async_client))
    world_id = create_response.json()["id"]

    response = await async_client.patch(
        f"/worlds/{world_id}", json={"name": "Renamed", "description": "New"}, headers=_csrf_headers(async_client)
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"
    assert response.json()["description"] == "New"
