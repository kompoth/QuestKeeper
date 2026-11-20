"""Shared service-layer exceptions, mapped to HTTP responses in `api.errors`."""


class EntityNotFoundError(Exception):
    pass


class WorldNotFoundError(Exception):
    pass


class InviteNotFoundError(Exception):
    pass


class InviteTokenNotFoundError(Exception):
    pass


class EmailAlreadyRegisteredError(Exception):
    pass


class PasswordResetTokenNotFoundError(Exception):
    pass


class RegistrationTokenNotFoundError(Exception):
    pass


class UserNotFoundError(Exception):
    """Raised for an admin-targeted user_id lookup - never used on a public, email-based path."""


class PermissionDeniedError(Exception):
    """Raised with (user_id, resource_id) for internal use - str() stays generic, since those ids reach the caller
    verbatim as the 403 response body otherwise."""

    def __str__(self) -> str:
        return "Permission denied"


class CannotBanSelfError(Exception):
    pass


class CannotChangeOwnRoleError(Exception):
    pass


class InvalidStatusTransitionError(Exception):
    pass


class IdCollisionError(Exception):
    """A newly generated World/Entity id already exists - the caller should regenerate and retry."""


class EntityNotInTrashError(Exception):
    """Raised when restore/restore-branch/purge targets an entity that exists but isn't soft-deleted."""


class WorldNotInTrashError(Exception):
    """Raised when restore/purge targets a world that exists but isn't soft-deleted."""


class UnsupportedMediaTypeError(Exception):
    """Raised when a media upload's declared content-type isn't on the image allow-list."""


class MediaTooLargeError(Exception):
    """Raised when a media upload's declared size exceeds the configured cap."""
