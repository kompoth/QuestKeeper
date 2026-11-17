"""Maps domain/service exceptions to HTTP responses, so routes stay free of try/except."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.adapters.db.repositories import InviteNotFoundError as SqlInviteNotFoundError
from app.services.access import (
    EmailAlreadyRegisteredError,
    EntityNotFoundError,
    InviteNotFoundError,
    InviteTokenNotFoundError,
    PasswordResetTokenNotFoundError,
    PermissionDeniedError,
    RegistrationTokenNotFoundError,
    UserNotFoundError,
    WorldNotFoundError,
)
from app.services.auth import InvalidCredentialsError, InvalidSessionError


def _not_found(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


def _forbidden(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": str(exc)})


def _unauthorized(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=401, content={"detail": str(exc)})


def _conflict(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


_NOT_FOUND_EXCEPTIONS = (
    EntityNotFoundError,
    WorldNotFoundError,
    InviteNotFoundError,
    InviteTokenNotFoundError,
    PasswordResetTokenNotFoundError,
    RegistrationTokenNotFoundError,
    UserNotFoundError,
    SqlInviteNotFoundError,
)


def register_exception_handlers(app: FastAPI) -> None:
    for exc_type in _NOT_FOUND_EXCEPTIONS:
        app.add_exception_handler(exc_type, _not_found)
    app.add_exception_handler(PermissionDeniedError, _forbidden)
    for exc_type in (InvalidCredentialsError, InvalidSessionError):
        app.add_exception_handler(exc_type, _unauthorized)
    app.add_exception_handler(EmailAlreadyRegisteredError, _conflict)
