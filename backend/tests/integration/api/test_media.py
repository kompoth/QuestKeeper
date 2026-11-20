"""Media upload/read against a real S3-compatible store (DATABASE_URL + S3_* must point at live
test instances - see CLAUDE.md's "Local convenience" section for the disposable containers).
"""

import httpx
import pytest

from tests.integration.api.conftest import csrf_headers, login

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _create_world_and_entity(async_client) -> tuple[str, str]:
    world_response = await async_client.post("/worlds", json={"name": "World"}, headers=csrf_headers(async_client))
    world_id = world_response.json()["id"]
    entity_response = await async_client.post(
        f"/worlds/{world_id}/entities", json={"name": "Page"}, headers=csrf_headers(async_client)
    )
    return world_id, entity_response.json()["id"]


async def _upload_real_bytes(mint_response: dict, content: bytes, *, content_type: str | None = None) -> httpx.Response:
    """POSTs directly to the live object store using a mint response's policy - no ASGI transport
    involved, since the whole point of this design is that the backend is never in this path."""
    fields = dict(mint_response["fields"])
    if content_type is not None:
        fields["Content-Type"] = content_type
    async with httpx.AsyncClient() as store_client:
        return await store_client.post(mint_response["url"], data=fields, files={"file": ("test.png", content)})


async def test_mint_upload_succeeds_with_write_access(async_client, db_session):
    await login(async_client, db_session)
    world_id, entity_id = await _create_world_and_entity(async_client)

    response = await async_client.post(
        f"/worlds/{world_id}/entities/{entity_id}/media",
        json={"content_type": "image/png", "size": 12},
        headers=csrf_headers(async_client),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["file_id"]
    assert body["url"]
    assert body["fields"]["key"] == f"worlds/{world_id}/entities/{entity_id}/{body['file_id']}"


async def test_mint_upload_rejects_unsupported_content_type(async_client, db_session):
    await login(async_client, db_session)
    world_id, entity_id = await _create_world_and_entity(async_client)

    response = await async_client.post(
        f"/worlds/{world_id}/entities/{entity_id}/media",
        json={"content_type": "image/svg+xml", "size": 12},
        headers=csrf_headers(async_client),
    )

    assert response.status_code == 415


async def test_mint_upload_rejects_oversized_declared_size(async_client, db_session):
    await login(async_client, db_session)
    world_id, entity_id = await _create_world_and_entity(async_client)

    response = await async_client.post(
        f"/worlds/{world_id}/entities/{entity_id}/media",
        json={"content_type": "image/png", "size": 999_999_999_999},
        headers=csrf_headers(async_client),
    )

    assert response.status_code == 413


async def test_upload_and_read_round_trip_against_the_real_store(async_client, db_session):
    await login(async_client, db_session)
    world_id, entity_id = await _create_world_and_entity(async_client)

    mint_response = await async_client.post(
        f"/worlds/{world_id}/entities/{entity_id}/media",
        json={"content_type": "image/png", "size": 12},
        headers=csrf_headers(async_client),
    )
    mint = mint_response.json()

    upload_response = await _upload_real_bytes(mint, b"hello-world!")
    assert upload_response.status_code // 100 == 2

    redirect_response = await async_client.get(f"/worlds/{world_id}/entities/{entity_id}/media/{mint['file_id']}")
    assert redirect_response.status_code == 302

    async with httpx.AsyncClient() as store_client:
        final_response = await store_client.get(redirect_response.headers["location"])
    assert final_response.status_code == 200
    assert final_response.content == b"hello-world!"


async def test_read_response_is_cacheable_only_as_long_as_its_signed_url_stays_valid(async_client, db_session):
    """Bounding Cache-Control to the signed URL's own TTL means a cached redirect can never outlive
    the URL it points to; `private` keeps it out of any shared/CDN cache, since access is per-user."""
    await login(async_client, db_session)
    world_id, entity_id = await _create_world_and_entity(async_client)
    mint = (
        await async_client.post(
            f"/worlds/{world_id}/entities/{entity_id}/media",
            json={"content_type": "image/png", "size": 12},
            headers=csrf_headers(async_client),
        )
    ).json()

    response = await async_client.get(f"/worlds/{world_id}/entities/{entity_id}/media/{mint['file_id']}")

    assert response.headers["cache-control"] == "private, max-age=60"


async def test_real_store_rejects_upload_exceeding_the_signed_size_condition(async_client, db_session):
    """The declared-size check at mint time is just a fast, friendly error - this is the guarantee
    that actually holds: the signed POST condition itself, enforced by the store, independent of
    whatever the client claims."""
    await login(async_client, db_session)
    world_id, entity_id = await _create_world_and_entity(async_client)
    mint = (
        await async_client.post(
            f"/worlds/{world_id}/entities/{entity_id}/media",
            json={"content_type": "image/png", "size": 12},
            headers=csrf_headers(async_client),
        )
    ).json()

    oversized = b"x" * (10 * 1024 * 1024 + 1)
    response = await _upload_real_bytes(mint, oversized)

    assert response.status_code == 400


async def test_real_store_rejects_upload_with_a_different_content_type_than_declared(async_client, db_session):
    await login(async_client, db_session)
    world_id, entity_id = await _create_world_and_entity(async_client)
    mint = (
        await async_client.post(
            f"/worlds/{world_id}/entities/{entity_id}/media",
            json={"content_type": "image/png", "size": 12},
            headers=csrf_headers(async_client),
        )
    ).json()

    response = await _upload_real_bytes(mint, b"hello-world!", content_type="image/svg+xml")

    assert response.status_code == 400


async def test_list_media_returns_uploaded_files(async_client, db_session):
    await login(async_client, db_session)
    world_id, entity_id = await _create_world_and_entity(async_client)
    mint = (
        await async_client.post(
            f"/worlds/{world_id}/entities/{entity_id}/media",
            json={"content_type": "image/png", "size": 12},
            headers=csrf_headers(async_client),
        )
    ).json()
    await _upload_real_bytes(mint, b"hello-world!")

    response = await async_client.get(f"/worlds/{world_id}/entities/{entity_id}/media")

    assert response.status_code == 200
    assert response.json() == [
        {"file_id": mint["file_id"], "path": f"/worlds/{world_id}/entities/{entity_id}/media/{mint['file_id']}"}
    ]


async def test_delete_media_permanently_removes_the_file_from_the_real_store(async_client, db_session):
    await login(async_client, db_session)
    world_id, entity_id = await _create_world_and_entity(async_client)
    mint = (
        await async_client.post(
            f"/worlds/{world_id}/entities/{entity_id}/media",
            json={"content_type": "image/png", "size": 12},
            headers=csrf_headers(async_client),
        )
    ).json()
    await _upload_real_bytes(mint, b"hello-world!")
    signed_get_url = (
        await async_client.get(f"/worlds/{world_id}/entities/{entity_id}/media/{mint['file_id']}")
    ).headers["location"]

    delete_response = await async_client.delete(
        f"/worlds/{world_id}/entities/{entity_id}/media/{mint['file_id']}", headers=csrf_headers(async_client)
    )
    assert delete_response.status_code == 204

    list_response = await async_client.get(f"/worlds/{world_id}/entities/{entity_id}/media")
    assert list_response.json() == []

    async with httpx.AsyncClient() as store_client:
        final_response = await store_client.get(signed_get_url)
    assert final_response.status_code == 404


async def test_purge_deletes_the_entitys_media_from_the_real_store(async_client, db_session):
    await login(async_client, db_session)
    world_id, entity_id = await _create_world_and_entity(async_client)
    mint = (
        await async_client.post(
            f"/worlds/{world_id}/entities/{entity_id}/media",
            json={"content_type": "image/png", "size": 12},
            headers=csrf_headers(async_client),
        )
    ).json()
    await _upload_real_bytes(mint, b"hello-world!")
    signed_get_url = (
        await async_client.get(f"/worlds/{world_id}/entities/{entity_id}/media/{mint['file_id']}")
    ).headers["location"]

    await async_client.delete(f"/worlds/{world_id}/entities/{entity_id}", headers=csrf_headers(async_client))
    purge_response = await async_client.delete(
        f"/worlds/{world_id}/entities/{entity_id}/purge", headers=csrf_headers(async_client)
    )
    assert purge_response.status_code == 204

    async with httpx.AsyncClient() as store_client:
        final_response = await store_client.get(signed_get_url)
    assert final_response.status_code == 404


async def test_replacing_a_maps_image_deletes_the_old_one_from_the_real_store(async_client, db_session):
    await login(async_client, db_session)
    world_id, entity_id = await _create_world_and_entity(async_client)

    old_mint = (
        await async_client.post(
            f"/worlds/{world_id}/entities/{entity_id}/media",
            json={"content_type": "image/png", "size": 12},
            headers=csrf_headers(async_client),
        )
    ).json()
    await _upload_real_bytes(old_mint, b"old-image!!!")
    old_pic_path = f"/worlds/{world_id}/entities/{entity_id}/media/{old_mint['file_id']}"
    old_signed_get_url = (await async_client.get(old_pic_path)).headers["location"]

    await async_client.put(
        f"/worlds/{world_id}/entities/{entity_id}/map",
        json={"pic": old_pic_path, "pins": []},
        headers=csrf_headers(async_client),
    )

    new_mint = (
        await async_client.post(
            f"/worlds/{world_id}/entities/{entity_id}/media",
            json={"content_type": "image/png", "size": 12},
            headers=csrf_headers(async_client),
        )
    ).json()
    await _upload_real_bytes(new_mint, b"new-image!!!")
    new_pic_path = f"/worlds/{world_id}/entities/{entity_id}/media/{new_mint['file_id']}"

    replace_response = await async_client.put(
        f"/worlds/{world_id}/entities/{entity_id}/map",
        json={"pic": new_pic_path, "pins": []},
        headers=csrf_headers(async_client),
    )
    assert replace_response.status_code == 200

    async with httpx.AsyncClient() as store_client:
        old_response = await store_client.get(old_signed_get_url)
    assert old_response.status_code == 404
