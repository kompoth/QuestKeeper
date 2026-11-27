"""Maps domain/service exceptions to HTTP responses, so routes stay free of try/except."""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.adapters.db.repositories import InviteNotFoundError as SqlInviteNotFoundError
from app.domain.mail import MailDeliveryError
from app.services.auth import InvalidCredentialsError, InvalidSessionError, UserBannedError, UserPendingError
from app.services.errors import (
    CannotBanSelfError,
    CannotChangeOwnRoleError,
    EmailAlreadyRegisteredError,
    EntityNotFoundError,
    EntityNotInTrashError,
    InvalidStatusTransitionError,
    InviteNotFoundError,
    InviteTokenNotFoundError,
    MapPinNotFoundError,
    MediaTooLargeError,
    PasswordResetTokenNotFoundError,
    PermissionDeniedError,
    RegistrationTokenNotFoundError,
    UnsupportedMediaTypeError,
    UserNotFoundError,
    WorldNotFoundError,
    WorldNotInTrashError,
)

logger = logging.getLogger(__name__)


def _not_found(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


def _forbidden(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": str(exc)})


def _unauthorized(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=401, content={"detail": str(exc)})


def _conflict(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


def _service_unavailable(_request: Request, exc: Exception) -> JSONResponse:
    logger.error("%s", exc, exc_info=exc)
    return JSONResponse(status_code=503, content={"detail": str(exc)})


def _payload_too_large(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=413, content={"detail": str(exc)})


def _unsupported_media_type(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=415, content={"detail": str(exc)})


_NOT_FOUND_EXCEPTIONS = (
    EntityNotFoundError,
    WorldNotFoundError,
    InviteNotFoundError,
    InviteTokenNotFoundError,
    PasswordResetTokenNotFoundError,
    RegistrationTokenNotFoundError,
    UserNotFoundError,
    SqlInviteNotFoundError,
    MapPinNotFoundError,
)


def register_exception_handlers(app: FastAPI) -> None:
    for exc_type in _NOT_FOUND_EXCEPTIONS:
        app.add_exception_handler(exc_type, _not_found)
    for exc_type in (
        PermissionDeniedError,
        CannotBanSelfError,
        CannotChangeOwnRoleError,
        UserBannedError,
        UserPendingError,
    ):
        app.add_exception_handler(exc_type, _forbidden)
    for exc_type in (InvalidCredentialsError, InvalidSessionError):
        app.add_exception_handler(exc_type, _unauthorized)
    for exc_type in (
        EmailAlreadyRegisteredError,
        InvalidStatusTransitionError,
        EntityNotInTrashError,
        WorldNotInTrashError,
    ):
        app.add_exception_handler(exc_type, _conflict)
    app.add_exception_handler(MailDeliveryError, _service_unavailable)
    app.add_exception_handler(MediaTooLargeError, _payload_too_large)
    app.add_exception_handler(UnsupportedMediaTypeError, _unsupported_media_type)
