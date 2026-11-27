"""Env-driven configuration via pydantic-settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# .env lives at the repo root, shared with the frontend - resolved from this file's own path
# rather than the CWD, so it's found regardless of where the process is launched from.
_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # extra="ignore": the shared .env also carries frontend-only vars (e.g. VITE_API_BASE_URL).
    model_config = SettingsConfigDict(env_file=_REPO_ROOT / ".env", extra="ignore")

    frontend_origin: str
    cookie_secure: bool = True

    database_url: str

    smtp_host: str
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    smtp_from_address: str

    # On startup, if the system has no admin yet, creates (or promotes) this account to admin.
    # Both or neither - a no-op once any admin exists, so safe to leave set indefinitely.
    seed_admin_email: str | None = None
    seed_admin_password: str | None = None

    # S3-compatible (Garage in dev, real AWS S3 in prod) object storage for entity media.
    s3_endpoint_url: str
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str
    s3_region: str = "us-east-1"

    media_max_upload_bytes: int = 40 * 1024 * 1024
    # Short on purpose: a fresh signature is minted on every request, so this only bounds how long a
    # copied/leaked URL stays usable - it doesn't need to survive longer than one page load.
    media_presign_ttl_seconds: int = 60


def get_settings() -> Settings:
    """Returns the process-wide cached `Settings`, built once from the environment.

    Tests that mutate the environment mid-run (e.g. toggling COOKIE_SECURE) must call
    `Settings.settings_clear_cache()` to force the next call here to rebuild from the new values -
    see the autouse fixture in tests/unit/test_config.py.
    """
    return Settings.settings_cached()
