"""Outbound media-storage port, implemented by app.adapters.media.S3MediaStorage.

Media is entity-scoped object storage (one file belongs to exactly one entity), served through
presigned S3/MinIO URLs so file bytes never pass through this backend - it only ever decides
whether to mint a signature, never streams a file itself.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class UploadPolicy:
    """A presigned POST policy letting the caller upload directly to the object store."""

    url: str
    fields: dict[str, str]


class MediaStorage(Protocol):
    async def create_upload_policy(
        self, *, key: str, content_type: str, max_bytes: int, ttl_seconds: int
    ) -> UploadPolicy:
        """A presigned POST policy for uploading exactly one object at `key`.

        `content_type` and `max_bytes` are baked into the policy's signed conditions (exact
        content-type match, content-length-range) - enforced by the store itself against the
        actual upload, not merely trusted from the caller.
        """
        ...

    async def generate_read_url(self, *, key: str, ttl_seconds: int) -> str:
        """A presigned GET URL for `key`, valid for `ttl_seconds`."""
        ...

    async def delete_prefix(self, *, prefix: str) -> None:
        """Deletes every object whose key starts with `prefix` - a no-op if none exist.

        Also used to delete one exact object, by passing its full key as `prefix`.
        """
        ...
