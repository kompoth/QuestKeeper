"""SMTP-backed Mailer adapter."""

from email.message import EmailMessage

import aiosmtplib

from app.config import (
    get_smtp_from_address,
    get_smtp_host,
    get_smtp_password,
    get_smtp_port,
    get_smtp_use_tls,
    get_smtp_username,
)


class SmtpMailer:
    async def send_existing_user_invite(self, *, to_email: str, world_name: str) -> None:
        message = self._build_message(
            to_email,
            subject=f"You've been invited to {world_name}",
            body=f"You've been invited to join the world '{world_name}' on Questkeeper. Log in and accept it.",
        )
        await self._send(message)

    async def send_new_user_invite(self, *, to_email: str, world_name: str, confirm_url: str) -> None:
        message = self._build_message(
            to_email,
            subject=f"You've been invited to {world_name}",
            body=(
                f"You've been invited to join the world '{world_name}' on Questkeeper. "
                f"Create your account to accept: {confirm_url}"
            ),
        )
        await self._send(message)

    async def send_password_reset(self, *, to_email: str, reset_url: str) -> None:
        message = self._build_message(
            to_email,
            subject="Reset your Questkeeper password",
            body=f"Use this link to reset your password: {reset_url}",
        )
        await self._send(message)

    async def send_registration_confirmation(self, *, to_email: str, confirm_url: str) -> None:
        message = self._build_message(
            to_email,
            subject="Confirm your Questkeeper account",
            body=f"Use this link to confirm your account and log in: {confirm_url}",
        )
        await self._send(message)

    def _build_message(self, to_email: str, *, subject: str, body: str) -> EmailMessage:
        message = EmailMessage()
        message["From"] = get_smtp_from_address()
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)
        return message

    async def _send(self, message: EmailMessage) -> None:
        await aiosmtplib.send(
            message,
            hostname=get_smtp_host(),
            port=get_smtp_port(),
            username=get_smtp_username(),
            password=get_smtp_password(),
            start_tls=get_smtp_use_tls(),
        )
