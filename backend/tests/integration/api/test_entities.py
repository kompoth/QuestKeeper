from datetime import UTC, datetime

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
    assert create_response.json()["access"] == {"read": True, "write": True, "can_delete": True}

    list_response = await async_client.get(f"/worlds/{world_id}/entities")
    assert list_response.status_code == 200
    [listed] = list_response.json()
    assert listed["id"] == entity_id
    assert listed["access"] == {"read": True, "write": True, "can_delete": True}


async def test_list_entities_reports_read_only_access_for_a_read_grantee(async_client, db_session):
    await _login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)
    create_response = await async_client.post(
        f"/worlds/{world_id}/entities", json={"name": "Root"}, headers=_csrf_headers(async_client)
    )
    entity_id = create_response.json()["id"]
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
        f"/worlds/{world_id}/permissions",
        json={"grantee_email": "grantee@example.com", "entity_id": entity_id, "level": "read"},
        headers=_csrf_headers(async_client),
    )

    await async_client.post("/auth/login", json={"email": "grantee@example.com", "password": PASSWORD})
    list_response = await async_client.get(f"/worlds/{world_id}/entities")

    assert list_response.status_code == 200
    [listed] = list_response.json()
    assert listed["access"] == {"read": True, "write": False, "can_delete": False}


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


async def test_delete_entity_soft_deletes_it(async_client, db_session):
    """Excluded from the live list, but a direct GET still returns it (read-only, flagged deleted_at) -
    trashed entities stay viewable for anyone who could already read them."""
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

    list_response = await async_client.get(f"/worlds/{world_id}/entities")
    assert entity_id not in [entity["id"] for entity in list_response.json()]

    get_response = await async_client.get(f"/worlds/{world_id}/entities/{entity_id}")
    assert get_response.status_code == 200
    assert get_response.json()["deleted_at"] is not None


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
    db_session.add(WorldRow(id="w2", owner_id="owner2", name="World 2", created_at=datetime.now(UTC)))
    await db_session.commit()
    await _login(async_client, db_session, user_id="other")

    response = await async_client.post(
        "/worlds/w2/entities", json={"name": "Root"}, headers=_csrf_headers(async_client)
    )

    assert response.status_code == 403


async def test_trash_lists_deleted_entities(async_client, db_session):
    await _login(async_client, db_session)
    world_id = await _create_world(async_client)
    create_response = await async_client.post(
        f"/worlds/{world_id}/entities", json={"name": "Root"}, headers=_csrf_headers(async_client)
    )
    entity_id = create_response.json()["id"]
    await async_client.delete(f"/worlds/{world_id}/entities/{entity_id}", headers=_csrf_headers(async_client))

    trash_response = await async_client.get(f"/worlds/{world_id}/entities/trash")

    assert trash_response.status_code == 200
    assert [entity["id"] for entity in trash_response.json()] == [entity_id]


async def test_restore_also_restores_a_still_trashed_parent(async_client, db_session):
    """Otherwise the child would come back alive but unreachable - its parent still wouldn't list it."""
    await _login(async_client, db_session)
    world_id = await _create_world(async_client)
    parent_response = await async_client.post(
        f"/worlds/{world_id}/entities", json={"name": "Parent"}, headers=_csrf_headers(async_client)
    )
    parent_id = parent_response.json()["id"]
    child_response = await async_client.post(
        f"/worlds/{world_id}/entities",
        json={"name": "Child", "parent_id": parent_id},
        headers=_csrf_headers(async_client),
    )
    child_id = child_response.json()["id"]
    await async_client.delete(f"/worlds/{world_id}/entities/{parent_id}", headers=_csrf_headers(async_client))

    restore_response = await async_client.post(
        f"/worlds/{world_id}/entities/{child_id}/restore", headers=_csrf_headers(async_client)
    )
    assert restore_response.status_code == 200

    live_ids = {entity["id"] for entity in (await async_client.get(f"/worlds/{world_id}/entities")).json()}
    assert child_id in live_ids
    assert parent_id in live_ids


async def test_restore_branch_restores_descendants(async_client, db_session):
    await _login(async_client, db_session)
    world_id = await _create_world(async_client)
    parent_response = await async_client.post(
        f"/worlds/{world_id}/entities", json={"name": "Parent"}, headers=_csrf_headers(async_client)
    )
    parent_id = parent_response.json()["id"]
    child_response = await async_client.post(
        f"/worlds/{world_id}/entities",
        json={"name": "Child", "parent_id": parent_id},
        headers=_csrf_headers(async_client),
    )
    child_id = child_response.json()["id"]
    await async_client.delete(f"/worlds/{world_id}/entities/{parent_id}", headers=_csrf_headers(async_client))

    restore_response = await async_client.post(
        f"/worlds/{world_id}/entities/{parent_id}/restore-branch", headers=_csrf_headers(async_client)
    )
    assert restore_response.status_code == 200

    live_ids = {entity["id"] for entity in (await async_client.get(f"/worlds/{world_id}/entities")).json()}
    assert parent_id in live_ids
    assert child_id in live_ids


async def test_purge_permanently_removes_the_entity(async_client, db_session):
    await _login(async_client, db_session)
    world_id = await _create_world(async_client)
    create_response = await async_client.post(
        f"/worlds/{world_id}/entities", json={"name": "Root"}, headers=_csrf_headers(async_client)
    )
    entity_id = create_response.json()["id"]
    await async_client.delete(f"/worlds/{world_id}/entities/{entity_id}", headers=_csrf_headers(async_client))

    purge_response = await async_client.delete(
        f"/worlds/{world_id}/entities/{entity_id}/purge", headers=_csrf_headers(async_client)
    )
    assert purge_response.status_code == 204

    assert (await async_client.get(f"/worlds/{world_id}/entities/{entity_id}")).status_code == 404
    assert (await async_client.get(f"/worlds/{world_id}/entities/trash")).json() == []


async def test_restore_raises_conflict_when_entity_is_not_in_trash(async_client, db_session):
    await _login(async_client, db_session)
    world_id = await _create_world(async_client)
    create_response = await async_client.post(
        f"/worlds/{world_id}/entities", json={"name": "Root"}, headers=_csrf_headers(async_client)
    )
    entity_id = create_response.json()["id"]

    response = await async_client.post(
        f"/worlds/{world_id}/entities/{entity_id}/restore", headers=_csrf_headers(async_client)
    )

    assert response.status_code == 409
