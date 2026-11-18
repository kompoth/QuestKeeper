import aiosmtplib
import pytest

from app.adapters.email import SmtpMailer
from app.domain.mail import MailDeliveryError


def make_mailer() -> SmtpMailer:
    return SmtpMailer(
        host="localhost", port=587, username=None, password=None, use_tls=False, from_address="from@example.com"
    )


async def test_send_wraps_a_connection_failure_in_mail_delivery_error(monkeypatch):
    async def _raise_connect_error(*_args, **_kwargs):
        raise OSError("Connect call failed")

    monkeypatch.setattr(aiosmtplib, "send", _raise_connect_error)

    with pytest.raises(MailDeliveryError):
        await make_mailer().send_password_reset(to_email="user@example.com", reset_url="https://example.com/reset")


async def test_send_wraps_an_smtp_error_in_mail_delivery_error(monkeypatch):
    async def _raise_smtp_error(*_args, **_kwargs):
        raise aiosmtplib.SMTPResponseException(550, "Mailbox unavailable")

    monkeypatch.setattr(aiosmtplib, "send", _raise_smtp_error)

    with pytest.raises(MailDeliveryError):
        await make_mailer().send_password_reset(to_email="user@example.com", reset_url="https://example.com/reset")
