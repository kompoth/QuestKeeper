from app.domain.models import RuntimeSettings
from app.services.settings import get_runtime_settings, update_runtime_settings
from tests.unit.services.fakes import make_repos


async def test_get_runtime_settings_returns_defaults_when_never_written():
    repos = make_repos()

    settings = await get_runtime_settings(repos)

    assert settings == RuntimeSettings(registration_enabled=True, password_reset_enabled=True)


async def test_update_runtime_settings_persists_the_new_values():
    repos = make_repos()

    updated = await update_runtime_settings(
        repos, RuntimeSettings(registration_enabled=False, password_reset_enabled=False)
    )

    assert updated == RuntimeSettings(registration_enabled=False, password_reset_enabled=False)
    assert await get_runtime_settings(repos) == RuntimeSettings(
        registration_enabled=False, password_reset_enabled=False
    )
