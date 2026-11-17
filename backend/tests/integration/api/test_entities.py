import pytest

from app.adapters.db.orm import UserRow, WorldRow
from app.domain.models import UserRole
from app.domain.security import hash_password

pytestmark = pytest.mark.asyncio(loop_scope="session")

EMAIL = "user@example.com"
PASSWORD = "correct horse battery staple"  # noqa: S105


async def _login(async_client, db_session, user_id="owner") -> None:
    db_session.add(
        UserRow(id=user_id, name="User", email=EMAIL, hashed_password=hash_password(PASSWORD), role=UserRole.MEMBER)
    )
    await db_session.commit()
    await async_client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})


def _csrf_headers(async_client) -> dict[str, str]:
    return {"X-CSRF-Token": async_client.cookies["csrf_token"]}


async def _create_world(async_client) -> str:
    response = await async_client.post("/worlds", json={"name": "World"}, headers=_csrf_headers(async_client))
    return response.json()["id"]


async def test_create_and_list_entities(async_client, db_session):
    await _login(async_client, db_session)
    world_id = await _create_world(async_client)

    create_response = await async_client.post(
        f"/worlds/{world_id}/entities", json={"name": "Root"}, headers=_csrf_headers(async_client)
    )
    assert create_response.status_code == 200
    entity_id = create_response.json()["id"]

    list_response = await async_client.get(f"/worlds/{world_id}/entities")
    assert list_response.status_code == 200
    assert [entity["id"] for entity in list_response.json()] == [entity_id]


async def test_get_entity_returns_404_when_not_found(async_client, db_session):
    await _login(async_client, db_session)
    world_id = await _create_world(async_client)

    response = await async_client.get(f"/worlds/{world_id}/entities/missing")

    assert response.status_code == 404


async def test_rename_entity_requires_csrf_header(async_client, db_session):
    await _login(async_client, db_session)
    world_id = await _create_world(async_client)
    create_response = await async_client.post(
        f"/worlds/{world_id}/entities", json={"name": "Root"}, headers=_csrf_headers(async_client)
    )
    entity_id = create_response.json()["id"]

    response = await async_client.patch(f"/worlds/{world_id}/entities/{entity_id}", json={"name": "Renamed"})

    assert response.status_code == 403


async def test_rename_entity_succeeds_for_the_owner(async_client, db_session):
    await _login(async_client, db_session)
    world_id = await _create_world(async_client)
    create_response = await async_client.post(
        f"/worlds/{world_id}/entities", json={"name": "Root"}, headers=_csrf_headers(async_client)
    )
    entity_id = create_response.json()["id"]

    response = await async_client.patch(
        f"/worlds/{world_id}/entities/{entity_id}", json={"name": "Renamed"}, headers=_csrf_headers(async_client)
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"


async def test_delete_entity_removes_it(async_client, db_session):
    await _login(async_client, db_session)
    world_id = await _create_world(async_client)
    create_response = await async_client.post(
        f"/worlds/{world_id}/entities", json={"name": "Root"}, headers=_csrf_headers(async_client)
    )
    entity_id = create_response.json()["id"]

    response = await async_client.delete(
        f"/worlds/{world_id}/entities/{entity_id}", headers=_csrf_headers(async_client)
    )
    assert response.status_code == 204

    get_response = await async_client.get(f"/worlds/{world_id}/entities/{entity_id}")
    assert get_response.status_code == 404


async def test_set_and_clear_article(async_client, db_session):
    await _login(async_client, db_session)
    world_id = await _create_world(async_client)
    create_response = await async_client.post(
        f"/worlds/{world_id}/entities", json={"name": "Root"}, headers=_csrf_headers(async_client)
    )
    entity_id = create_response.json()["id"]

    set_response = await async_client.put(
        f"/worlds/{world_id}/entities/{entity_id}/article",
        json={"markdown": "# Hello"},
        headers=_csrf_headers(async_client),
    )
    assert set_response.status_code == 200
    assert set_response.json()["article"]["markdown"] == "# Hello"

    clear_response = await async_client.delete(
        f"/worlds/{world_id}/entities/{entity_id}/article", headers=_csrf_headers(async_client)
    )
    assert clear_response.status_code == 200
    assert clear_response.json()["article"] is None


async def test_set_and_clear_map(async_client, db_session):
    await _login(async_client, db_session)
    world_id = await _create_world(async_client)
    create_response = await async_client.post(
        f"/worlds/{world_id}/entities", json={"name": "Root"}, headers=_csrf_headers(async_client)
    )
    entity_id = create_response.json()["id"]
    pinned_response = await async_client.post(
        f"/worlds/{world_id}/entities", json={"name": "Pinned"}, headers=_csrf_headers(async_client)
    )
    pinned_id = pinned_response.json()["id"]

    set_response = await async_client.put(
        f"/worlds/{world_id}/entities/{entity_id}/map",
        json={"pic": "map.png", "pins": [{"entity_id": pinned_id, "x": 1, "y": 2}]},
        headers=_csrf_headers(async_client),
    )
    assert set_response.status_code == 200
    assert set_response.json()["map"]["pic"] == "map.png"

    clear_response = await async_client.delete(
        f"/worlds/{world_id}/entities/{entity_id}/map", headers=_csrf_headers(async_client)
    )
    assert clear_response.status_code == 200
    assert clear_response.json()["map"] is None


async def test_create_root_entity_requires_world_ownership(async_client, db_session):
    db_session.add(
        UserRow(id="owner2", name="Owner2", email="owner2@example.com", hashed_password="x", role=UserRole.MEMBER)
    )
    db_session.add(WorldRow(id="w2", owner_id="owner2", name="World 2"))
    await db_session.commit()
    await _login(async_client, db_session, user_id="other")

    response = await async_client.post(
        "/worlds/w2/entities", json={"name": "Root"}, headers=_csrf_headers(async_client)
    )

    assert response.status_code == 403
