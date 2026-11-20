"""Request/response schemas for shapes the domain models don't fit directly.

`World` is returned as-is from most routes - it's already a clean Pydantic model with nothing
sensitive to hide. The world list is the exception: it's wrapped by `WorldOut` below, to carry the
owner's display name alongside it. `Entity` is wrapped by `EntityOut` below too, to carry the
caller's resolved access alongside it. `WorldInvite` is not returned as-is either: it carries
`confirmation_token` (a credential) and `invitee_id` (privacy-sensitive) - see `InviteSummary` and
`PendingInviteOut` below, which redact both.
"""

from datetime import datetime

from pydantic import BaseModel

from app.domain.models import (
    Entity,
    EntityId,
    Map,
    MapPin,
    PermissionLevel,
    RuntimeSettings,
    UserId,
    UserRole,
    UserStatus,
    World,
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


class WorldOut(World):
    """`World` plus the owner's display name, for a list the caller didn't create themselves."""

    owner_name: str


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


class GrantPermissionRequest(BaseModel):
    entity_id: EntityId
    grantee_email: str
    level: PermissionLevel


class EntityGrantOut(BaseModel):
    """A user's permission level on an entity, enriched with the user's email/name for display.

    `name` is null for a still-unregistered grantee - revealing it would leak that identity the
    same way an unaccepted invite's name would.
    """

    user_id: UserId
    email: str
    name: str | None
    level: PermissionLevel


class InheritedEntityGrantOut(EntityGrantOut):
    """An `EntityGrantOut` inherited from an ancestor entity, rather than granted directly."""

    from_entity_id: EntityId


class EntityPermissionsOut(BaseModel):
    direct: list[EntityGrantOut]
    inherited: list[InheritedEntityGrantOut]


class CreateInviteRequest(BaseModel):
    invitee_email: str


class ConfirmInviteRequest(BaseModel):
    token: str
    name: str
    password: str


class InviteSummary(BaseModel):
    """The owner's view of an invite: email/name + status, never invitee_id or the token.

    `invitee_name` is null until the invite is accepted - revealing it any earlier would leak
    whether the invitee already had a registered account, before they themselves chose to accept.
    """

    invitee_email: str
    invitee_name: str | None
    accepted: bool

    @classmethod
    def from_invite(cls, invite: WorldInvite, invitee_email: str, invitee_name: str | None) -> InviteSummary:
        return cls(invitee_email=invitee_email, invitee_name=invitee_name, accepted=invite.accepted)


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
