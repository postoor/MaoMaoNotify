"""Notification and per-device Delivery (§49–51).

Notification is user-level (read state lives here, §51). Delivery is device-
level and tracks its own status (§50). Interactive actions/responses and audio
assets get their own tables in later phases; for now inline ``actions`` /
``voice`` JSON round-trips the agent payload.
"""

from datetime import datetime
from functools import partial

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.ids import new_id
from app.db.base import Base
from app.models.mixins import TimestampMixin, _utcnow
from app.notifications.constants import (
    DEFAULT_ROUTING_MODE,
    PRESENTATION_NORMAL,
    PRIORITY_NORMAL,
    STATUS_CREATED,
    TYPE_TEXT,
)


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=partial(new_id, "msg"))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    agent_id: Mapped[str | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True
    )

    title: Mapped[str | None] = mapped_column(String, nullable=True)
    message: Mapped[str | None] = mapped_column(String, nullable=True)
    type: Mapped[str] = mapped_column(String, default=TYPE_TEXT)
    priority: Mapped[str] = mapped_column(String, default=PRIORITY_NORMAL)
    presentation: Mapped[str] = mapped_column(String, default=PRESENTATION_NORMAL)

    routing_mode: Mapped[str] = mapped_column(String, default=DEFAULT_ROUTING_MODE)
    routing: Mapped[dict] = mapped_column(JSON, default=dict)
    voice: Mapped[dict] = mapped_column(JSON, default=dict)
    playback: Mapped[dict] = mapped_column(JSON, default=dict)
    actions: Mapped[list] = mapped_column(JSON, default=list)

    correlation_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    thread_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    group_key: Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    status: Mapped[str] = mapped_column(String, default=STATUS_CREATED)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # user-level read state (§51)

    # First-response-wins resolution (§44).
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_action_id: Mapped[str | None] = mapped_column(String, nullable=True)
    responded_by_device_id: Mapped[str | None] = mapped_column(String, nullable=True)

    deliveries: Mapped[list["NotificationDelivery"]] = relationship(
        back_populates="notification", cascade="all, delete-orphan"
    )
    responses: Mapped[list["NotificationResponse"]] = relationship(
        back_populates="notification", cascade="all, delete-orphan"
    )


class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=partial(new_id, "deliv"))
    notification_id: Mapped[str] = mapped_column(
        ForeignKey("notifications.id", ondelete="CASCADE"), index=True
    )
    device_id: Mapped[str] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String)
    order_index: Mapped[int] = mapped_column(default=0)  # position in the routing plan

    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    displayed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    played_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    notification: Mapped[Notification] = relationship(back_populates="deliveries")


class NotificationResponse(Base):
    __tablename__ = "notification_responses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=partial(new_id, "resp"))
    notification_id: Mapped[str] = mapped_column(
        ForeignKey("notifications.id", ondelete="CASCADE"), index=True
    )
    device_id: Mapped[str | None] = mapped_column(String, nullable=True)
    action_id: Mapped[str] = mapped_column(String)
    value: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    notification: Mapped[Notification] = relationship(back_populates="responses")
