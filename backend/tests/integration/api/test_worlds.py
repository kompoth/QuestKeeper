from datetime import UTC, datetime

import httpx
import pytest

from app.adapters.db.orm import EntityPermissionRow, EntityRow, UserRow, WorldInviteRow, WorldRow
from app.domain.models import PermissionLevel, UserRole
from app.domain.security import hash_password

pytestmark = pytest.mark.asyncio(loop_scope="session")

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
    db_session.add(WorldRow(id=world_id, owner_id=owner_id, name="World", created_at=datetime.now(UTC)))
    await db_session.commit()


def _csrf_headers(async_client) -> dict[str, str]:
    return {"X-CSRF-Token": async_client.cookies["csrf_token"]}


async def _create_world_via_api(async_client) -> str:
    response = await async_client.post("/worlds", json={"name": "World"}, headers=_csrf_headers(async_client))
    return response.json()["id"]


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


async def test_list_my_worlds_includes_owner_name_for_a_world_held_via_invite(async_client, db_session):
    await _login(async_client, db_session)
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


async def test_list_my_worlds_excludes_a_world_with_only_an_entity_grant_and_no_invite(async_client, db_session):
    await _login(async_client, db_session)
    await _create_owned_world(db_session)
    now = datetime.now(UTC)
    db_session.add(
        EntityRow(
            id="e1", world_id="w1", name="Root", created_at=now, updated_at=now, created_by="owner", updated_by="owner"
        )
    )
    await db_session.commit()
    db_session.add(EntityPermissionRow(user_id="u1", entity_id="e1", level=PermissionLevel.READ))
    await db_session.commit()

    response = await async_client.get("/worlds")

    assert response.status_code == 200
    assert response.json() == []


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


async def test_delete_world_requires_csrf_header(async_client, db_session):
    await _login(async_client, db_session, user_id="owner")
    world_id = await _create_world_via_api(async_client)

    response = await async_client.delete(f"/worlds/{world_id}")

    assert response.status_code == 403


async def test_deleted_world_moves_from_the_live_list_to_trash(async_client, db_session):
    await _login(async_client, db_session, user_id="owner")
    world_id = await _create_world_via_api(async_client)

    delete_response = await async_client.delete(f"/worlds/{world_id}", headers=_csrf_headers(async_client))
    assert delete_response.status_code == 204

    assert (await async_client.get("/worlds")).json() == []
    [trashed] = (await async_client.get("/worlds/trash")).json()
    assert trashed["id"] == world_id


async def test_list_world_trash_requires_a_session(async_client):
    response = await async_client.get("/worlds/trash")

    assert response.status_code == 401


async def test_restore_world_requires_ownership(async_client, db_session):
    await _create_owned_world(db_session)
    world_row = await db_session.get(WorldRow, "w1")
    world_row.deleted_at = datetime.now(UTC)
    await db_session.commit()
    await _login(async_client, db_session, user_id="u1")

    response = await async_client.post("/worlds/w1/restore", headers=_csrf_headers(async_client))

    assert response.status_code == 403


async def test_restore_world_brings_it_back_to_the_live_list(async_client, db_session):
    await _login(async_client, db_session, user_id="owner")
    world_id = await _create_world_via_api(async_client)
    await async_client.delete(f"/worlds/{world_id}", headers=_csrf_headers(async_client))

    restore_response = await async_client.post(f"/worlds/{world_id}/restore", headers=_csrf_headers(async_client))
    assert restore_response.status_code == 200
    assert restore_response.json()["id"] == world_id
    assert restore_response.json()["deleted_at"] is None

    assert [w["id"] for w in (await async_client.get("/worlds")).json()] == [world_id]
    assert (await async_client.get("/worlds/trash")).json() == []


async def test_purge_world_raises_conflict_when_not_in_trash(async_client, db_session):
    await _login(async_client, db_session, user_id="owner")
    world_id = await _create_world_via_api(async_client)

    response = await async_client.delete(f"/worlds/{world_id}/purge", headers=_csrf_headers(async_client))

    assert response.status_code == 409


async def test_purge_world_deletes_entities_and_their_media_from_the_real_store(async_client, db_session):
    await _login(async_client, db_session, user_id="owner")
    world_id = await _create_world_via_api(async_client)
    entity_id = (
        await async_client.post(
            f"/worlds/{world_id}/entities", json={"name": "Page"}, headers=_csrf_headers(async_client)
        )
    ).json()["id"]

    mint = (
        await async_client.post(
            f"/worlds/{world_id}/entities/{entity_id}/media",
            json={"content_type": "image/png", "size": 12},
            headers=_csrf_headers(async_client),
        )
    ).json()
    async with httpx.AsyncClient() as store_client:
        fields = dict(mint["fields"])
        await store_client.post(mint["url"], data=fields, files={"file": ("test.png", b"hello-world!")})
    signed_get_url = (
        await async_client.get(f"/worlds/{world_id}/entities/{entity_id}/media/{mint['file_id']}")
    ).headers["location"]

    await async_client.delete(f"/worlds/{world_id}", headers=_csrf_headers(async_client))
    purge_response = await async_client.delete(f"/worlds/{world_id}/purge", headers=_csrf_headers(async_client))
    assert purge_response.status_code == 204

    assert (await async_client.get(f"/worlds/{world_id}")).status_code == 404
    async with httpx.AsyncClient() as store_client:
        final_response = await store_client.get(signed_get_url)
    assert final_response.status_code == 404
