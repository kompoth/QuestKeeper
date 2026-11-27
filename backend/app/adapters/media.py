"""MediaStorage adapter for AWS S3 or any S3-compatible store (Garage in dev)."""

from collections.abc import Sequence

import aioboto3
import boto3
from botocore.config import Config

from app.domain.media import UploadPolicy


class S3MediaStorage:
    def __init__(self, *, endpoint_url: str, access_key: str, secret_key: str, bucket: str, region: str) -> None:
        self._bucket = bucket
        self._client_kwargs = {
            "endpoint_url": endpoint_url,
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "region_name": region,
        }
        self._session = aioboto3.Session()
        # Presigning (generate_presigned_post/url) is pure local HMAC signing - no network call - so
        # a plain sync boto3 client is used for it, rather than aioboto3's async client, which only
        # wraps real I/O operations (delete, list) as coroutines.
        self._presign_client = boto3.client("s3", config=Config(signature_version="s3v4"), **self._client_kwargs)

    async def create_upload_policy(
        self, *, key: str, content_type: str, max_bytes: int, ttl_seconds: int
    ) -> UploadPolicy:
        response = self._presign_client.generate_presigned_post(
            self._bucket,
            key,
            Fields={"Content-Type": content_type},
            Conditions=[
                ["content-length-range", 0, max_bytes],
                ["eq", "$Content-Type", content_type],
            ],
            ExpiresIn=ttl_seconds,
        )
        return UploadPolicy(url=response["url"], fields=response["fields"])

    async def generate_read_url(self, *, key: str, ttl_seconds: int) -> str:
        return self._presign_client.generate_presigned_url(
            "get_object", Params={"Bucket": self._bucket, "Key": key}, ExpiresIn=ttl_seconds
        )

    async def delete_prefix(self, *, prefix: str) -> None:
        async with self._session.resource("s3", **self._client_kwargs) as s3:
            bucket = await s3.Bucket(self._bucket)
            await bucket.objects.filter(Prefix=prefix).delete()

    async def list_objects(self, *, prefix: str) -> Sequence[str]:
        async with self._session.resource("s3", **self._client_kwargs) as s3:
            bucket = await s3.Bucket(self._bucket)
            return [obj.key async for obj in bucket.objects.filter(Prefix=prefix)]

    async def ensure_cors(self, *, allowed_origin: str) -> None:
        async with self._session.client("s3", **self._client_kwargs) as s3:
            await s3.put_bucket_cors(
                Bucket=self._bucket,
                CORSConfiguration={
                    "CORSRules": [
                        {
                            "AllowedMethods": ["GET", "PUT", "POST", "HEAD"],
                            "AllowedOrigins": [allowed_origin],
                            "AllowedHeaders": ["*"],
                            "ExposeHeaders": ["ETag"],
                        }
                    ]
                },
            )
