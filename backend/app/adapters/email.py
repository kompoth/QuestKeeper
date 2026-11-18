"""SMTP-backed Mailer adapter."""

from email.message import EmailMessage

import aiosmtplib


class SmtpMailer:
    def __init__(  # noqa: PLR0913 -- distinct SMTP connection/identity params, not data fields
        self,
        *,
        host: str,
        port: int,
        username: str | None,
        password: str | None,
        use_tls: bool,
        from_address: str,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._use_tls = use_tls
        self._from_address = from_address

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
        message["From"] = self._from_address
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)
        return message

    async def _send(self, message: EmailMessage) -> None:
        await aiosmtplib.send(
            message,
            hostname=self._host,
            port=self._port,
            username=self._username,
            password=self._password,
            start_tls=self._use_tls,
        )
