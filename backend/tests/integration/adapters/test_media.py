"""S3MediaStorage.ensure_cors against a real S3-compatible store (see CLAUDE.md's "Local
convenience" section for the disposable containers)."""

import boto3
import pytest

from app.composition import build_media_storage
from app.config import get_settings

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_ensure_cors_sets_bucket_policy_for_frontend_origin():
    settings = get_settings()
    storage = build_media_storage()

    await storage.ensure_cors(allowed_origin=settings.frontend_origin)

    client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
    )
    rules = client.get_bucket_cors(Bucket=settings.s3_bucket)["CORSRules"]

    assert len(rules) == 1
    assert settings.frontend_origin in rules[0]["AllowedOrigins"]
    assert set(rules[0]["AllowedMethods"]) >= {"GET", "PUT", "POST", "HEAD"}
