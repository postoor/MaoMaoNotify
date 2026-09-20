"""Agent scopes (§8)."""

NOTIFICATION_SEND = "notification:send"
NOTIFICATION_READ = "notification:read"
NOTIFICATION_BROADCAST = "notification:broadcast"
NOTIFICATION_TARGET_DEVICE = "notification:target_device"
PRESENCE_READ = "presence:read"
ACTION_RECEIVE = "action:receive"

ALL_SCOPES = frozenset({
    NOTIFICATION_SEND,
    NOTIFICATION_READ,
    NOTIFICATION_BROADCAST,
    NOTIFICATION_TARGET_DEVICE,
    PRESENCE_READ,
    ACTION_RECEIVE,
})

# Granted by default when none are specified. Broadcast / target_device are
# intentionally excluded — they must be granted explicitly (§8).
DEFAULT_SCOPES = frozenset({
    NOTIFICATION_SEND,
    NOTIFICATION_READ,
    ACTION_RECEIVE,
})


def has_scopes(granted: list[str] | set[str], required: list[str] | set[str]) -> bool:
    return set(required).issubset(set(granted))
