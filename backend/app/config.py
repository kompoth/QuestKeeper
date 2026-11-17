"""Env-driven configuration, one function per variable."""

import os


def get_frontend_origin() -> str:
    return os.environ["FRONTEND_ORIGIN"]


def get_cookie_secure() -> bool:
    return os.environ.get("COOKIE_SECURE", "true").lower() != "false"


def get_smtp_host() -> str:
    return os.environ["SMTP_HOST"]


def get_smtp_port() -> int:
    return int(os.environ.get("SMTP_PORT", "587"))


def get_smtp_username() -> str | None:
    return os.environ.get("SMTP_USERNAME")


def get_smtp_password() -> str | None:
    return os.environ.get("SMTP_PASSWORD")


def get_smtp_use_tls() -> bool:
    return os.environ.get("SMTP_USE_TLS", "true").lower() != "false"


def get_smtp_from_address() -> str:
    return os.environ["SMTP_FROM_ADDRESS"]


def get_registration_enabled() -> bool:
    return os.environ.get("REGISTRATION_ENABLED", "true").lower() != "false"


def get_password_reset_enabled() -> bool:
    return os.environ.get("PASSWORD_RESET_ENABLED", "true").lower() != "false"
