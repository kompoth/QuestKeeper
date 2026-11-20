from datetime import UTC, datetime

import httpx
import pytest

from app.adapters.db.orm import EntityPermissionRow, EntityRow, UserRow, WorldInviteRow, WorldRow
from app.domain.models import PermissionLevel, UserRole
from tests.integration.api.conftest import csrf_headers, login

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _create_owned_world(db_session, world_id="w1", owner_id="owner") -> None:
    db_session.add(
        UserRow(id=owner_id, name="Owner", email="owner@example.com", hashed_password="x", role=UserRole.MEMBER)
    )
    db_session.add(WorldRow(id=world_id, owner_id=owner_id, name="World", created_at=datetime.now(UTC)))
    await db_session.commit()


async def _create_world_via_api(async_client) -> str:
    response = await async_client.post("/worlds", json={"name": "World"}, headers=csrf_headers(async_client))
    return response.json()["id"]


async def test_list_my_worlds_requires_a_session(async_client):
    response = await async_client.get("/worlds")

    assert response.status_code == 401


async def test_create_world_requires_csrf_header(async_client, db_session):
    await login(async_client, db_session, user_id="u1")

    response = await async_client.post("/worlds", json={"name": "New World"})

    assert response.status_code == 403


async def test_list_my_worlds_includes_owner_name_for_a_world_held_via_invite(async_client, db_session):
    await login(async_client, db_session, user_id="u1")
    await _create_owned_world(db_session)
    now = datetime.now(UTC)
    db_session.add(
        EntityRow(
            id="e1", world_id="w1", name="Root", created_at=now, updated_at=now, created_by="owner", updated_by="owner"
        )
    )
    await db_session.commit()
    db_session.add(WorldInviteRow(id="i1", world_id="w1", invitee_id="u1"))
    db_session.add(EntityPermissionRow(user_id="u1", entity_id="e1", level=PermissionLevel.READ))
    await db_session.commit()

    response = await async_client.get("/worlds")

    assert response.status_code == 200
    [world] = response.json()
    assert world["owner_name"] == "Owner"


async def test_delete_world_requires_csrf_header(async_client, db_session):
    await login(async_client, db_session, user_id="owner")
    world_id = await _create_world_via_api(async_client)

    response = await async_client.delete(f"/worlds/{world_id}")

    assert response.status_code == 403


async def test_list_world_trash_requires_a_session(async_client):
    response = await async_client.get("/worlds/trash")

    assert response.status_code == 401


async def test_purge_world_deletes_entities_and_their_media_from_the_real_store(async_client, db_session):
    await login(async_client, db_session, user_id="owner")
    world_id = await _create_world_via_api(async_client)
    entity_id = (
        await async_client.post(
            f"/worlds/{world_id}/entities", json={"name": "Page"}, headers=csrf_headers(async_client)
        )
    ).json()["id"]

    mint = (
        await async_client.post(
            f"/worlds/{world_id}/entities/{entity_id}/media",
            json={"content_type": "image/png", "size": 12},
            headers=csrf_headers(async_client),
        )
    ).json()
    async with httpx.AsyncClient() as store_client:
        fields = dict(mint["fields"])
        await store_client.post(mint["url"], data=fields, files={"file": ("test.png", b"hello-world!")})
    signed_get_url = (
        await async_client.get(f"/worlds/{world_id}/entities/{entity_id}/media/{mint['file_id']}")
    ).headers["location"]

    await async_client.delete(f"/worlds/{world_id}", headers=csrf_headers(async_client))
    purge_response = await async_client.delete(f"/worlds/{world_id}/purge", headers=csrf_headers(async_client))
    assert purge_response.status_code == 204

    assert (await async_client.get(f"/worlds/{world_id}")).status_code == 404
    async with httpx.AsyncClient() as store_client:
        final_response = await store_client.get(signed_get_url)
    assert final_response.status_code == 404
