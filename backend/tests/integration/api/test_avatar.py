"""Avatar (global media) upload/read against a real S3-compatible store (DATABASE_URL + S3_* must
point at live test instances - see CLAUDE.md's "Local convenience" section for the disposable
containers).
"""

import httpx
import pytest

from tests.integration.api.conftest import csrf_headers, login

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _upload_real_bytes(mint_response: dict, content: bytes, *, content_type: str | None = None) -> httpx.Response:
    fields = dict(mint_response["fields"])
    if content_type is not None:
        fields["Content-Type"] = content_type
    async with httpx.AsyncClient() as store_client:
        return await store_client.post(mint_response["url"], data=fields, files={"file": ("test.png", content)})


async def test_mint_upload_succeeds_for_a_logged_in_user(async_client, db_session):
    await login(async_client, db_session)

    response = await async_client.post(
        "/users/me/avatar/upload", json={"content_type": "image/png", "size": 12}, headers=csrf_headers(async_client)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["file_id"]
    assert body["fields"]["key"] == f"global/{body['file_id']}"


async def test_mint_upload_rejects_unsupported_content_type(async_client, db_session):
    await login(async_client, db_session)

    response = await async_client.post(
        "/users/me/avatar/upload",
        json={"content_type": "image/svg+xml", "size": 12},
        headers=csrf_headers(async_client),
    )

    assert response.status_code == 415


async def test_mint_upload_rejects_oversized_declared_size(async_client, db_session):
    await login(async_client, db_session)

    response = await async_client.post(
        "/users/me/avatar/upload",
        json={"content_type": "image/png", "size": 999_999_999_999},
        headers=csrf_headers(async_client),
    )

    assert response.status_code == 413


async def test_set_avatar_round_trips_against_the_real_store(async_client, db_session):
    await login(async_client, db_session)
    mint = (
        await async_client.post(
            "/users/me/avatar/upload",
            json={"content_type": "image/png", "size": 12},
            headers=csrf_headers(async_client),
        )
    ).json()
    await _upload_real_bytes(mint, b"hello-world!")

    put_response = await async_client.put(
        "/users/me/avatar", json={"file_id": mint["file_id"]}, headers=csrf_headers(async_client)
    )
    assert put_response.status_code == 200
    avatar_path = put_response.json()["avatar"]
    assert avatar_path == f"/media/{mint['file_id']}"

    redirect_response = await async_client.get(avatar_path)
    assert redirect_response.status_code == 302
    async with httpx.AsyncClient() as store_client:
        final_response = await store_client.get(redirect_response.headers["location"])
    assert final_response.status_code == 200
    assert final_response.content == b"hello-world!"


async def test_any_logged_in_user_may_read_another_users_avatar(async_client, db_session):
    await login(async_client, db_session, user_id="owner", email="owner@example.com")
    mint = (
        await async_client.post(
            "/users/me/avatar/upload",
            json={"content_type": "image/png", "size": 12},
            headers=csrf_headers(async_client),
        )
    ).json()
    await _upload_real_bytes(mint, b"hello-world!")
    avatar_path = (
        await async_client.put(
            "/users/me/avatar", json={"file_id": mint["file_id"]}, headers=csrf_headers(async_client)
        )
    ).json()["avatar"]

    await login(async_client, db_session, user_id="other", email="other@example.com")
    response = await async_client.get(avatar_path)

    assert response.status_code == 302


async def test_read_avatar_requires_a_session(async_client, db_session):
    await login(async_client, db_session)
    mint = (
        await async_client.post(
            "/users/me/avatar/upload",
            json={"content_type": "image/png", "size": 12},
            headers=csrf_headers(async_client),
        )
    ).json()
    avatar_path = (
        await async_client.put(
            "/users/me/avatar", json={"file_id": mint["file_id"]}, headers=csrf_headers(async_client)
        )
    ).json()["avatar"]
    await async_client.post("/auth/logout", headers=csrf_headers(async_client))

    response = await async_client.get(avatar_path)

    assert response.status_code == 401


async def test_replacing_the_avatar_deletes_the_old_one_from_the_real_store(async_client, db_session):
    await login(async_client, db_session)
    old_mint = (
        await async_client.post(
            "/users/me/avatar/upload",
            json={"content_type": "image/png", "size": 12},
            headers=csrf_headers(async_client),
        )
    ).json()
    await _upload_real_bytes(old_mint, b"old-avatar!!")
    old_avatar_path = (
        await async_client.put(
            "/users/me/avatar", json={"file_id": old_mint["file_id"]}, headers=csrf_headers(async_client)
        )
    ).json()["avatar"]
    old_signed_get_url = (await async_client.get(old_avatar_path)).headers["location"]

    new_mint = (
        await async_client.post(
            "/users/me/avatar/upload",
            json={"content_type": "image/png", "size": 12},
            headers=csrf_headers(async_client),
        )
    ).json()
    await _upload_real_bytes(new_mint, b"new-avatar!!")
    put_response = await async_client.put(
        "/users/me/avatar", json={"file_id": new_mint["file_id"]}, headers=csrf_headers(async_client)
    )
    assert put_response.status_code == 200

    async with httpx.AsyncClient() as store_client:
        old_response = await store_client.get(old_signed_get_url)
    assert old_response.status_code == 404


async def test_clear_avatar_removes_it_and_deletes_the_file_from_the_real_store(async_client, db_session):
    await login(async_client, db_session)
    mint = (
        await async_client.post(
            "/users/me/avatar/upload",
            json={"content_type": "image/png", "size": 12},
            headers=csrf_headers(async_client),
        )
    ).json()
    await _upload_real_bytes(mint, b"hello-world!")
    await async_client.put("/users/me/avatar", json={"file_id": mint["file_id"]}, headers=csrf_headers(async_client))
    signed_get_url = (await async_client.get(f"/media/{mint['file_id']}")).headers["location"]

    delete_response = await async_client.delete("/users/me/avatar", headers=csrf_headers(async_client))
    assert delete_response.status_code == 200
    assert delete_response.json()["avatar"] is None

    async with httpx.AsyncClient() as store_client:
        final_response = await store_client.get(signed_get_url)
    assert final_response.status_code == 404
