"""Admin-editable runtime settings, backed by the database."""

from app.domain.models import RuntimeSettings
from app.domain.repositories import Repositories


async def get_runtime_settings(repos: Repositories) -> RuntimeSettings:
    return await repos.runtime_settings.get()


async def update_runtime_settings(repos: Repositories, settings: RuntimeSettings) -> RuntimeSettings:
    await repos.runtime_settings.update(settings)
    return settings
