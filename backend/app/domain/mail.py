"""Outbound email port, implemented by app.adapters.email.SmtpMailer."""

from typing import Protocol


class MailDeliveryError(Exception):
    """Raised by a Mailer implementation when a send fails - e.g. the SMTP server is unreachable."""


class Mailer(Protocol):
    async def send_existing_user_invite(self, *, to_email: str, world_name: str) -> None: ...

    async def send_new_user_invite(self, *, to_email: str, world_name: str, confirm_url: str) -> None: ...

    async def send_password_reset(self, *, to_email: str, reset_url: str) -> None: ...

    async def send_registration_confirmation(self, *, to_email: str, confirm_url: str) -> None: ...
