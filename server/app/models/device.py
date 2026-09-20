"""Device registry, device credentials, device preferences, pairing tokens."""

from datetime import datetime
from functools import partial

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.ids import new_id
from app.db.base import Base
from app.models.mixins import TimestampMixin, _utcnow


class Device(Base, TimestampMixin):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=partial(new_id, "dev"))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    detected_name: Mapped[str | None] = mapped_column(String, nullable=True)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    platform: Mapped[str] = mapped_column(String)  # macos | linux | android
    architecture: Mapped[str | None] = mapped_column(String, nullable=True)
    capabilities: Mapped[list] = mapped_column(JSON, default=list)  # §11
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # UnifiedPush endpoint (§56 alt) — self-hosted push wake for background Android.
    push_endpoint: Mapped[str | None] = mapped_column(String, nullable=True)

    credential: Mapped["DeviceCredential"] = relationship(
        back_populates="device", cascade="all, delete-orphan", uselist=False
    )
    preferences: Mapped["DevicePreferences"] = relationship(
        back_populates="device", cascade="all, delete-orphan", uselist=False
    )


class DeviceCredential(Base):
    __tablename__ = "device_credentials"

    device_id: Mapped[str] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True
    )
    public_key: Mapped[str | None] = mapped_column(String, nullable=True)
    token_hash: Mapped[str] = mapped_column(String, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    device: Mapped[Device] = relationship(back_populates="credential")


class DevicePreferences(Base, TimestampMixin):
    __tablename__ = "device_preferences"

    device_id: Mapped[str] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True
    )
    voice_policy: Mapped[dict] = mapped_column(JSON, default=dict)  # §37
    data: Mapped[dict] = mapped_column(JSON, default=dict)

    device: Mapped[Device] = relationship(back_populates="preferences")


class PairingToken(Base):
    __tablename__ = "pairing_tokens"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=partial(new_id, "pair"))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String, unique=True, index=True)
    code: Mapped[str] = mapped_column(String, index=True)  # 8-digit console code
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    device_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
