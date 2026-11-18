"""Composition root: assembles concrete adapters into the Repositories/Mailer ports.

Framework-agnostic - importable by FastAPI's request-scoped dependencies
(app/api/dependencies.py) or by anything else (background tasks, scripts) that needs real
repositories without going through FastAPI's dependency graph.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.repositories import (
    SqlEntityPermissionRepository,
    SqlEntityRepository,
    SqlPasswordResetRepository,
    SqlPendingRegistrationRepository,
    SqlSessionRepository,
    SqlUserRepository,
    SqlWorldInviteRepository,
    SqlWorldRepository,
)
from app.adapters.email import SmtpMailer
from app.config import get_settings
from app.domain.mail import Mailer
from app.domain.repositories import Repositories


def build_repositories(session: AsyncSession) -> Repositories:
    return Repositories(
        users=SqlUserRepository(session),
        worlds=SqlWorldRepository(session),
        entities=SqlEntityRepository(session),
        permissions=SqlEntityPermissionRepository(session),
        invites=SqlWorldInviteRepository(session),
        sessions=SqlSessionRepository(session),
        password_resets=SqlPasswordResetRepository(session),
        pending_registrations=SqlPendingRegistrationRepository(session),
        commit=session.commit,
    )


def build_mailer() -> Mailer:
    settings = get_settings()
    return SmtpMailer(
        host=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_username,
        password=settings.smtp_password,
        use_tls=settings.smtp_use_tls,
        from_address=settings.smtp_from_address,
    )
