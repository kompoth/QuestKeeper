"""Request/response schemas for shapes the domain models don't fit directly.

`World` and `EntityPermission` are returned or accepted as-is elsewhere — they're already clean
Pydantic models with nothing sensitive to hide. `Entity` is wrapped by `EntityOut` below, to carry
the caller's resolved access alongside it. `WorldInvite` is not returned as-is either: it carries
`confirmation_token` (a credential) and `invitee_id` (privacy-sensitive) - see `InviteSummary`
and `PendingInviteOut` below, which redact both.
"""

from datetime import datetime

from pydantic import BaseModel

from app.domain.models import (
    Entity,
    EntityId,
    Map,
    MapPin,
    RuntimeSettings,
    UserId,
    UserRole,
    UserStatus,
    WorldId,
    WorldInvite,
)
from app.domain.permissions import EntityAccess


class UserOut(BaseModel):
    id: UserId
    name: str
    email: str
    role: UserRole
    status: UserStatus
    joined_at: datetime


class LoginRequest(BaseModel):
    email: str
    password: str


class CreateWorldRequest(BaseModel):
    name: str
    description: str | None = None
    pic: str | None = None


class UpdateWorldRequest(BaseModel):
    name: str
    description: str | None = None
    pic: str | None = None


class EntityAccessOut(BaseModel):
    read: bool
    write: bool
    can_delete: bool

    @classmethod
    def from_access(cls, access: EntityAccess) -> EntityAccessOut:
        return cls(read=access.read, write=access.write, can_delete=access.can_delete)


class EntityOut(Entity):
    """`Entity` plus the caller's resolved access to it, for permission-aware frontend UI."""

    access: EntityAccessOut

    @classmethod
    def from_entity(cls, entity: Entity, access: EntityAccess) -> EntityOut:
        return cls(**entity.model_dump(), access=EntityAccessOut.from_access(access))


class CreateEntityRequest(BaseModel):
    name: str
    parent_id: EntityId | None = None


class RenameEntityRequest(BaseModel):
    name: str


class SetArticleRequest(BaseModel):
    markdown: str


class SetMapRequest(BaseModel):
    pic: str
    pins: list[MapPin] = []

    def to_map(self) -> Map:
        return Map(pic=self.pic, pins={(pin.x, pin.y): pin for pin in self.pins})


class CreateInviteRequest(BaseModel):
    invitee_email: str


class ConfirmInviteRequest(BaseModel):
    token: str
    name: str
    password: str


class InviteSummary(BaseModel):
    """The owner's view of an invite: email + status, never invitee_id or the token."""

    invitee_email: str
    accepted: bool

    @classmethod
    def from_invite(cls, invite: WorldInvite, invitee_email: str) -> InviteSummary:
        return cls(invitee_email=invitee_email, accepted=invite.accepted)


class PendingInviteOut(BaseModel):
    """The invitee's own view of a pending invite: world + status, no invitee_id or token."""

    world_id: WorldId
    accepted: bool

    @classmethod
    def from_invite(cls, invite: WorldInvite) -> PendingInviteOut:
        return cls(world_id=invite.world_id, accepted=invite.accepted)


class RequestPasswordResetRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class ConfirmRegistrationRequest(BaseModel):
    token: str


class RuntimeSettingsOut(BaseModel):
    registration_enabled: bool
    password_reset_enabled: bool

    @classmethod
    def from_settings(cls, settings: RuntimeSettings) -> RuntimeSettingsOut:
        return cls(
            registration_enabled=settings.registration_enabled,
            password_reset_enabled=settings.password_reset_enabled,
        )


class RuntimeSettingsUpdate(BaseModel):
    registration_enabled: bool
    password_reset_enabled: bool

    def to_settings(self) -> RuntimeSettings:
        return RuntimeSettings(
            registration_enabled=self.registration_enabled, password_reset_enabled=self.password_reset_enabled
        )


class UserListOut(BaseModel):
    users: list[UserOut]
    total: int


class RoleUpdate(BaseModel):
    role: UserRole


class CreateUserRequest(BaseModel):
    name: str
    email: str
    role: UserRole


class StatusUpdate(BaseModel):
    status: UserStatus
