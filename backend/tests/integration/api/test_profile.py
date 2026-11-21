"""Self-service account profile routes."""

import pytest

from tests.integration.api.conftest import csrf_headers, login

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_put_name_changes_the_callers_own_name(async_client, db_session):
    await login(async_client, db_session)

    response = await async_client.put("/users/me/name", json={"name": "New name"}, headers=csrf_headers(async_client))

    assert response.status_code == 200
    assert response.json()["name"] == "New name"

    me = await async_client.get("/auth/me")
    assert me.json()["name"] == "New name"
