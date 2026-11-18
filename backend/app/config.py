"""Env-driven configuration via pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    frontend_origin: str
    cookie_secure: bool = True

    database_url: str

    smtp_host: str
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    smtp_from_address: str

    registration_enabled: bool = True
    password_reset_enabled: bool = True


def get_settings() -> Settings:
    """Returns the process-wide cached `Settings`, built once from the environment.

    Tests that mutate the environment mid-run (e.g. toggling REGISTRATION_ENABLED) must call
    `Settings.settings_clear_cache()` to force the next call here to rebuild from the new values -
    see the autouse fixture in tests/integration/conftest.py.
    """
    return Settings.settings_cached()
