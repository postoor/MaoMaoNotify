"""Redis key builders and TTLs (§68)."""

PRESENCE_TTL = 120  # seconds; presence is Redis-TTL only (§52)
ACTIVITY_TTL = 120
ACTIVE_TTL = 300
IDEMPOTENCY_TTL = 86_400  # 24h (§46)


def presence(user_id: str, device_id: str) -> str:
    return f"presence:{user_id}:{device_id}"


def presence_pattern(user_id: str) -> str:
    return f"presence:{user_id}:*"


def activity(user_id: str, device_id: str) -> str:
    return f"activity:{user_id}:{device_id}"


def activity_pattern(user_id: str) -> str:
    return f"activity:{user_id}:*"


def active(user_id: str) -> str:
    return f"active:{user_id}"


def ws_device(device_id: str) -> str:
    return f"ws:device:{device_id}"


def idempotency(agent_id: str, key: str) -> str:
    return f"idempotency:{agent_id}:{key}"
