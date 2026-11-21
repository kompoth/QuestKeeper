import pytest

from tests.integration.api.conftest import csrf_headers, login

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _create_world(async_client) -> str:
    response = await async_client.post("/worlds", json={"name": "World"}, headers=csrf_headers(async_client))
    return response.json()["id"]


async def test_create_and_list_entities(async_client, db_session):
    await login(async_client, db_session)
    world_id = await _create_world(async_client)

    create_response = await async_client.post(
        f"/worlds/{world_id}/entities", json={"name": "Root"}, headers=csrf_headers(async_client)
    )
    assert create_response.status_code == 200
    entity_id = create_response.json()["id"]
    assert create_response.json()["access"] == {"read": True, "write": True, "can_delete": True}

    list_response = await async_client.get(f"/worlds/{world_id}/entities")
    assert list_response.status_code == 200
    [listed] = list_response.json()
    assert listed["id"] == entity_id
    assert listed["access"] == {"read": True, "write": True, "can_delete": True}


async def test_delete_entity_soft_deletes_it(async_client, db_session):
    """Excluded from the live list, but a direct GET still returns it (read-only, flagged deleted_at) -
    trashed entities stay viewable for anyone who could already read them."""
    await login(async_client, db_session)
    world_id = await _create_world(async_client)
    create_response = await async_client.post(
        f"/worlds/{world_id}/entities", json={"name": "Root"}, headers=csrf_headers(async_client)
    )
    entity_id = create_response.json()["id"]

    response = await async_client.delete(f"/worlds/{world_id}/entities/{entity_id}", headers=csrf_headers(async_client))
    assert response.status_code == 204

    list_response = await async_client.get(f"/worlds/{world_id}/entities")
    assert entity_id not in [entity["id"] for entity in list_response.json()]

    get_response = await async_client.get(f"/worlds/{world_id}/entities/{entity_id}")
    assert get_response.status_code == 200
    assert get_response.json()["deleted_at"] is not None
