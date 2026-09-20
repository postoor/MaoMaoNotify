"""Notification enums, defaults, and timing (§21–24, §40, §49, §53)."""

# Types (§21)
TYPE_TEXT = "text"
TYPE_VOICE = "voice"
TYPES = frozenset({TYPE_TEXT, TYPE_VOICE})

# Voice sources (§25–34)
VOICE_CLIENT_TTS = "client_tts"
VOICE_SERVER_TTS = "server_tts"
VOICE_AGENT_AUDIO = "agent_audio"
VOICE_SOURCES = frozenset({VOICE_CLIENT_TTS, VOICE_SERVER_TTS, VOICE_AGENT_AUDIO})

# Priority (§23)
PRIORITY_LOW = "low"
PRIORITY_NORMAL = "normal"
PRIORITY_HIGH = "high"
PRIORITY_CRITICAL = "critical"
PRIORITIES = frozenset({PRIORITY_LOW, PRIORITY_NORMAL, PRIORITY_HIGH, PRIORITY_CRITICAL})

# Routing modes (§24)
ROUTE_ACTIVE_ONLY = "active_only"
ROUTE_ACTIVE_WITH_FALLBACK = "active_with_fallback"
ROUTE_ALL_DEVICES = "all_devices"
ROUTE_SPECIFIC_DEVICE = "specific_device"
ROUTING_MODES = frozenset({
    ROUTE_ACTIVE_ONLY, ROUTE_ACTIVE_WITH_FALLBACK, ROUTE_ALL_DEVICES, ROUTE_SPECIFIC_DEVICE,
})
DEFAULT_ROUTING_MODE = ROUTE_ACTIVE_WITH_FALLBACK

# Presentation (§48)
PRESENTATION_NORMAL = "normal"
PRESENTATION_SILENT = "silent"

# TTL defaults in seconds by priority (§40)
TTL_DEFAULTS = {
    PRIORITY_LOW: 30 * 60,
    PRIORITY_NORMAL: 24 * 60 * 60,
    PRIORITY_HIGH: 24 * 60 * 60,
    PRIORITY_CRITICAL: 24 * 60 * 60,
}

# Fallback timeout in seconds by priority (§53)
FALLBACK_TIMEOUT = {
    PRIORITY_LOW: 5,
    PRIORITY_NORMAL: 5,
    PRIORITY_HIGH: 2,
    PRIORITY_CRITICAL: 2,
}

# Notification lifecycle (§49) — user-facing status
STATUS_CREATED = "created"
STATUS_QUEUED = "queued"
STATUS_ROUTED = "routed"
STATUS_SENT = "sent"
STATUS_DELIVERED = "delivered"
STATUS_DISPLAYED = "displayed"
STATUS_PLAYED = "played"
STATUS_OPENED = "opened"
STATUS_RESPONDED = "responded"
STATUS_EXPIRED = "expired"
STATUS_FAILED = "failed"

# Notification actions (§41–43). confirm / open_url are reserved for later.
ACTION_BUTTON = "button"
ACTION_TEXT_INPUT = "text_input"
ACTION_TYPES = frozenset({ACTION_BUTTON, ACTION_TEXT_INPUT})

# Agent event names (§65)
EVENT_DELIVERED = "notification.delivered"
EVENT_PLAYED = "notification.played"
EVENT_OPENED = "notification.opened"
EVENT_EXPIRED = "notification.expired"
EVENT_FAILED = "notification.failed"
EVENT_RESPONDED = "notification.responded"

# Per-device delivery status (§50)
DELIVERY_ROUTED = "routed"
DELIVERY_SENT = "sent"
DELIVERY_DELIVERED = "delivered"
DELIVERY_DISPLAYED = "displayed"
DELIVERY_PLAYED = "played"
DELIVERY_OPENED = "opened"
DELIVERY_FAILED = "failed"
DELIVERY_FALLBACK_CANCELLED = "fallback_cancelled"
