"""World pic upload/read against a real S3-compatible store (DATABASE_URL + S3_* must point at live
test instances - see CLAUDE.md's "Local convenience" section for the disposable containers).
"""

import httpx
import pytest

from app.adapters.db.orm import UserRow, WorldInviteRow
from app.domain.models import UserRole
from app.domain.security import hash_password
from tests.integration.api.conftest import PASSWORD, csrf_headers, login

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _create_world(async_client) -> str:
    response = await async_client.post("/api/worlds", json={"name": "World"}, headers=csrf_headers(async_client))
    return response.json()["id"]


async def _register_user(db_session, user_id: str, email: str) -> None:
    db_session.add(
        UserRow(id=user_id, name=user_id, email=email, hashed_password=hash_password(PASSWORD), role=UserRole.MEMBER)
    )
    await db_session.commit()


async def _upload_real_bytes(mint_response: dict, content: bytes, *, content_type: str | None = None) -> httpx.Response:
    fields = dict(mint_response["fields"])
    if content_type is not None:
        fields["Content-Type"] = content_type
    async with httpx.AsyncClient() as store_client:
        return await store_client.post(mint_response["url"], data=fields, files={"file": ("test.png", content)})


async def test_mint_pic_upload_succeeds_for_owner(async_client, db_session):
    await login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)

    response = await async_client.post(
        f"/api/worlds/{world_id}/pic",
        json={"content_type": "image/png", "size": 12},
        headers=csrf_headers(async_client),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["file_id"]
    assert body["fields"]["key"] == f"worlds/{world_id}/pic/{body['file_id']}"


async def test_mint_pic_upload_rejects_a_non_owner(async_client, db_session):
    await login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)

    await login(async_client, db_session, user_id="other", email="other@example.com")
    response = await async_client.post(
        f"/api/worlds/{world_id}/pic",
        json={"content_type": "image/png", "size": 12},
        headers=csrf_headers(async_client),
    )

    assert response.status_code == 403


async def test_mint_pic_upload_rejects_unsupported_content_type(async_client, db_session):
    await login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)

    response = await async_client.post(
        f"/api/worlds/{world_id}/pic",
        json={"content_type": "image/svg+xml", "size": 12},
        headers=csrf_headers(async_client),
    )

    assert response.status_code == 415


async def test_mint_pic_upload_rejects_oversized_declared_size(async_client, db_session):
    await login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)

    response = await async_client.post(
        f"/api/worlds/{world_id}/pic",
        json={"content_type": "image/png", "size": 999_999_999_999},
        headers=csrf_headers(async_client),
    )

    assert response.status_code == 413


async def test_upload_attach_and_read_round_trip_against_the_real_store(async_client, db_session):
    await login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)

    mint = (
        await async_client.post(
            f"/api/worlds/{world_id}/pic",
            json={"content_type": "image/png", "size": 12},
            headers=csrf_headers(async_client),
        )
    ).json()
    await _upload_real_bytes(mint, b"hello-world!")
    pic_path = f"/api/worlds/{world_id}/pic/{mint['file_id']}"

    patch_response = await async_client.patch(
        f"/api/worlds/{world_id}", json={"name": "World", "pic": pic_path}, headers=csrf_headers(async_client)
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["pic"] == pic_path

    redirect_response = await async_client.get(pic_path)
    assert redirect_response.status_code == 302
    async with httpx.AsyncClient() as store_client:
        final_response = await store_client.get(redirect_response.headers["location"])
    assert final_response.status_code == 200
    assert final_response.content == b"hello-world!"


async def test_read_pic_succeeds_for_a_user_with_only_an_unaccepted_invite(async_client, db_session):
    await login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)
    mint = (
        await async_client.post(
            f"/api/worlds/{world_id}/pic",
            json={"content_type": "image/png", "size": 12},
            headers=csrf_headers(async_client),
        )
    ).json()
    await _upload_real_bytes(mint, b"hello-world!")
    pic_path = f"/api/worlds/{world_id}/pic/{mint['file_id']}"
    await async_client.patch(
        f"/api/worlds/{world_id}", json={"name": "World", "pic": pic_path}, headers=csrf_headers(async_client)
    )
    await _register_user(db_session, "invitee", "invitee@example.com")
    db_session.add(WorldInviteRow(id="i1", world_id=world_id, invitee_id="invitee"))
    await db_session.commit()

    await async_client.post("/api/auth/login", json={"email": "invitee@example.com", "password": PASSWORD})
    response = await async_client.get(pic_path)

    assert response.status_code == 302


async def test_read_pic_rejects_a_user_with_no_access_to_the_world(async_client, db_session):
    await login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)
    mint = (
        await async_client.post(
            f"/api/worlds/{world_id}/pic",
            json={"content_type": "image/png", "size": 12},
            headers=csrf_headers(async_client),
        )
    ).json()
    await _upload_real_bytes(mint, b"hello-world!")
    pic_path = f"/api/worlds/{world_id}/pic/{mint['file_id']}"
    await async_client.patch(
        f"/api/worlds/{world_id}", json={"name": "World", "pic": pic_path}, headers=csrf_headers(async_client)
    )

    await login(async_client, db_session, user_id="stranger", email="stranger@example.com")
    response = await async_client.get(pic_path)

    assert response.status_code == 403


async def test_replacing_the_pic_deletes_the_old_one_from_the_real_store(async_client, db_session):
    await login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)

    old_mint = (
        await async_client.post(
            f"/api/worlds/{world_id}/pic",
            json={"content_type": "image/png", "size": 12},
            headers=csrf_headers(async_client),
        )
    ).json()
    await _upload_real_bytes(old_mint, b"old-pic!!!!!")
    old_pic_path = f"/api/worlds/{world_id}/pic/{old_mint['file_id']}"
    await async_client.patch(
        f"/api/worlds/{world_id}", json={"name": "World", "pic": old_pic_path}, headers=csrf_headers(async_client)
    )
    old_signed_get_url = (await async_client.get(old_pic_path)).headers["location"]

    new_mint = (
        await async_client.post(
            f"/api/worlds/{world_id}/pic",
            json={"content_type": "image/png", "size": 12},
            headers=csrf_headers(async_client),
        )
    ).json()
    await _upload_real_bytes(new_mint, b"new-pic!!!!!")
    new_pic_path = f"/api/worlds/{world_id}/pic/{new_mint['file_id']}"
    replace_response = await async_client.patch(
        f"/api/worlds/{world_id}", json={"name": "World", "pic": new_pic_path}, headers=csrf_headers(async_client)
    )
    assert replace_response.status_code == 200

    async with httpx.AsyncClient() as store_client:
        old_response = await store_client.get(old_signed_get_url)
    assert old_response.status_code == 404


async def test_purge_world_deletes_the_pic_from_the_real_store(async_client, db_session):
    await login(async_client, db_session, user_id="owner")
    world_id = await _create_world(async_client)
    mint = (
        await async_client.post(
            f"/api/worlds/{world_id}/pic",
            json={"content_type": "image/png", "size": 12},
            headers=csrf_headers(async_client),
        )
    ).json()
    await _upload_real_bytes(mint, b"hello-world!")
    pic_path = f"/api/worlds/{world_id}/pic/{mint['file_id']}"
    await async_client.patch(
        f"/api/worlds/{world_id}", json={"name": "World", "pic": pic_path}, headers=csrf_headers(async_client)
    )
    signed_get_url = (await async_client.get(pic_path)).headers["location"]

    await async_client.delete(f"/api/worlds/{world_id}", headers=csrf_headers(async_client))
    purge_response = await async_client.delete(f"/api/worlds/{world_id}/purge", headers=csrf_headers(async_client))
    assert purge_response.status_code == 204

    async with httpx.AsyncClient() as store_client:
        final_response = await store_client.get(signed_get_url)
    assert final_response.status_code == 404
