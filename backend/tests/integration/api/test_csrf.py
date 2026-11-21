"""Global, method-based CSRF enforcement: unsafe methods need a matching cookie/header pair.

Per-route exemptions (login, register, register/confirm, password-recovery, password-reset)
are proven by their own happy-path tests in test_auth.py succeeding without a CSRF header.
"""

import pytest

from tests.integration.api.conftest import csrf_headers, login

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_unsafe_method_without_csrf_token_is_rejected(async_client, db_session):
    await login(async_client, db_session)

    response = await async_client.post("/worlds", json={"name": "World"})

    assert response.status_code == 403


async def test_unsafe_method_with_mismatched_csrf_token_is_rejected(async_client, db_session):
    await login(async_client, db_session)

    response = await async_client.post("/worlds", json={"name": "World"}, headers={"X-CSRF-Token": "wrong"})

    assert response.status_code == 403


async def test_unsafe_method_with_matching_csrf_token_succeeds(async_client, db_session):
    await login(async_client, db_session)

    response = await async_client.post("/worlds", json={"name": "World"}, headers=csrf_headers(async_client))

    assert response.status_code == 200


async def test_safe_method_does_not_require_csrf_token(async_client, db_session):
    await login(async_client, db_session)

    response = await async_client.get("/worlds")

    assert response.status_code == 200
