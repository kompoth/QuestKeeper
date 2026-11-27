import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings


@pytest.fixture(autouse=True)
def _reset_settings_cache(monkeypatch):
    """get_settings() is process-cached; these tests mutate the env per-test and need a clean
    cache before (to force a fresh read) and after (so the next test isn't left with this one's
    cached value).

    Also disables dotenv loading: a developer's local `backend/.env` would otherwise be read as a
    fallback for any env var these tests delete, making "missing"/"default" assertions depend on
    whatever that file happens to contain.
    """
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    Settings.settings_clear_cache()
    yield
    Settings.settings_clear_cache()


def _set_required_env(monkeypatch) -> None:
    monkeypatch.setenv("FRONTEND_ORIGIN", "http://localhost:5173")
    monkeypatch.setenv("DATABASE_URL", "mysql+aiomysql://user:pass@localhost/test")
    monkeypatch.setenv("SMTP_HOST", "localhost")
    monkeypatch.setenv("SMTP_FROM_ADDRESS", "test@example.com")
    monkeypatch.setenv("S3_ENDPOINT_URL", "http://localhost:9000")
    monkeypatch.setenv("S3_ACCESS_KEY", "test")
    monkeypatch.setenv("S3_SECRET_KEY", "test")
    monkeypatch.setenv("S3_BUCKET", "test-bucket")


def test_get_settings_reads_values_from_env(monkeypatch):
    monkeypatch.setenv("FRONTEND_ORIGIN", "http://example.com")
    monkeypatch.setenv("DATABASE_URL", "mysql+aiomysql://user:pass@localhost/test")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_FROM_ADDRESS", "noreply@example.com")
    monkeypatch.setenv("S3_ENDPOINT_URL", "http://localhost:9000")
    monkeypatch.setenv("S3_ACCESS_KEY", "test")
    monkeypatch.setenv("S3_SECRET_KEY", "test")
    monkeypatch.setenv("S3_BUCKET", "test-bucket")

    settings = get_settings()

    assert settings.frontend_origin == "http://example.com"
    assert settings.database_url == "mysql+aiomysql://user:pass@localhost/test"
    assert settings.smtp_host == "smtp.example.com"
    assert settings.smtp_from_address == "noreply@example.com"


def test_get_settings_raises_when_a_required_field_is_missing(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError):
        get_settings()


def test_optional_fields_fall_back_to_defaults(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    monkeypatch.delenv("SMTP_PORT", raising=False)

    settings = get_settings()

    assert settings.cookie_secure is True
    assert settings.smtp_port == 587
    assert settings.smtp_username is None
