"""SQLAlchemy table mappings. Row classes are storage shapes, not domain models."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domain.models import PermissionLevel, UserRole, UserStatus

ID_LENGTH = 36


class Base(DeclarativeBase):
    pass


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(ID_LENGTH), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, native_enum=False, length=20))
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, native_enum=False, length=20), default=UserStatus.ACTIVE
    )
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class WorldRow(Base):
    __tablename__ = "worlds"

    id: Mapped[str] = mapped_column(String(ID_LENGTH), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(ID_LENGTH), ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    pic: Mapped[str | None] = mapped_column(String(512), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, index=True, default=None)


class EntityRow(Base):
    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(String(ID_LENGTH), primary_key=True)
    world_id: Mapped[str] = mapped_column(String(ID_LENGTH), ForeignKey("worlds.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    parent_id: Mapped[str | None] = mapped_column(
        String(ID_LENGTH), ForeignKey("entities.id"), index=True, default=None
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, index=True, default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    created_by: Mapped[str] = mapped_column(String(ID_LENGTH), ForeignKey("users.id"))
    updated_by: Mapped[str] = mapped_column(String(ID_LENGTH), ForeignKey("users.id"))

    article: Mapped[ArticleRow | None] = relationship(back_populates="entity", uselist=False)
    map: Mapped[MapRow | None] = relationship(back_populates="entity", uselist=False)


class ArticleRow(Base):
    __tablename__ = "articles"

    entity_id: Mapped[str] = mapped_column(String(ID_LENGTH), ForeignKey("entities.id"), primary_key=True)
    markdown: Mapped[str] = mapped_column(Text)

    entity: Mapped[EntityRow] = relationship(back_populates="article")


class MapRow(Base):
    __tablename__ = "maps"

    entity_id: Mapped[str] = mapped_column(String(ID_LENGTH), ForeignKey("entities.id"), primary_key=True)
    pic: Mapped[str] = mapped_column(String(512))

    entity: Mapped[EntityRow] = relationship(back_populates="map")
    pins: Mapped[list[MapPinRow]] = relationship(back_populates="map", cascade="all, delete-orphan")


class MapPinRow(Base):
    __tablename__ = "map_pins"

    map_entity_id: Mapped[str] = mapped_column(String(ID_LENGTH), ForeignKey("maps.entity_id"), primary_key=True)
    x: Mapped[float] = mapped_column(Float, primary_key=True)
    y: Mapped[float] = mapped_column(Float, primary_key=True)
    pinned_entity_id: Mapped[str] = mapped_column(String(ID_LENGTH), ForeignKey("entities.id"))

    map: Mapped[MapRow] = relationship(back_populates="pins")


class EntityPermissionRow(Base):
    __tablename__ = "entity_permissions"

    user_id: Mapped[str] = mapped_column(String(ID_LENGTH), ForeignKey("users.id"), primary_key=True)
    entity_id: Mapped[str] = mapped_column(String(ID_LENGTH), ForeignKey("entities.id"), primary_key=True)
    level: Mapped[PermissionLevel] = mapped_column(Enum(PermissionLevel, native_enum=False, length=10))


class SessionRow(Base):
    __tablename__ = "sessions"

    token: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(ID_LENGTH), ForeignKey("users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class WorldInviteRow(Base):
    """One row per (world, invitee): re-inviting an already-pending invitee updates it in place."""

    __tablename__ = "world_invites"
    __table_args__ = (UniqueConstraint("world_id", "invitee_id", name="uq_world_invites_world_id_invitee_id"),)

    id: Mapped[str] = mapped_column(String(ID_LENGTH), primary_key=True)
    world_id: Mapped[str] = mapped_column(String(ID_LENGTH), ForeignKey("worlds.id"), index=True)
    invitee_id: Mapped[str] = mapped_column(String(ID_LENGTH), ForeignKey("users.id"), index=True)
    accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmation_token: Mapped[str | None] = mapped_column(String(64), unique=True, default=None)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)


class PasswordResetRow(Base):
    """One row per user: a new reset request replaces the user's existing outstanding one."""

    __tablename__ = "password_resets"

    user_id: Mapped[str] = mapped_column(String(ID_LENGTH), ForeignKey("users.id"), primary_key=True)
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class RegistrationConfirmationRow(Base):
    """One row per user: a new registration request replaces the user's existing outstanding one."""

    __tablename__ = "registration_confirmations"

    user_id: Mapped[str] = mapped_column(String(ID_LENGTH), ForeignKey("users.id"), primary_key=True)
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class RuntimeSettingsRow(Base):
    """Single row (fixed `id`), upserted in place by admin edits."""

    __tablename__ = "runtime_settings"

    id: Mapped[str] = mapped_column(String(ID_LENGTH), primary_key=True)
    registration_enabled: Mapped[bool] = mapped_column(Boolean)
    password_reset_enabled: Mapped[bool] = mapped_column(Boolean)
