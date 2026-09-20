"""SQLAlchemy 2 ORM models (Phase 1: users, devices, agents).

Importing this package registers every model on ``Base.metadata`` so Alembic
autogenerate and ``create_all`` see them. Notification tables land in Phase 2.
"""

from app.models.agent import Agent, AgentToken, AgentWebhook
from app.models.app_setting import AppSetting
from app.models.audio import AudioAsset
from app.models.device import Device, DeviceCredential, DevicePreferences, PairingToken
from app.models.notification import (
    Notification,
    NotificationDelivery,
    NotificationResponse,
)
from app.models.user import RefreshToken, User, UserCredential, UserPreferences

__all__ = [
    "Agent",
    "AgentToken",
    "AgentWebhook",
    "AppSetting",
    "AudioAsset",
    "Device",
    "DeviceCredential",
    "DevicePreferences",
    "Notification",
    "NotificationDelivery",
    "NotificationResponse",
    "PairingToken",
    "RefreshToken",
    "User",
    "UserCredential",
    "UserPreferences",
]
