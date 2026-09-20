"""Redis-backed presence + active-device selection with hysteresis (§17, §18).

Presence lives in Redis with TTL only (§52); a device whose keys have expired is
treated as offline.
"""

import json
import time

from redis.asyncio import Redis

from app.core import redis_keys
from app.presence.schemas import ActiveDeviceOut, Observation, PresenceSnapshot
from app.presence.scoring import compute_activity_score, confidence_from_score

SWITCH_THRESHOLD = 15  # §18
MIN_HOLD_MS = 30_000  # §18


# Baseline activity for a device that is WS-connected but hasn't reported an
# observation yet — enough to read as online (not offline), refined by the
# client's presence loop (§16).
_CONNECTED_BASELINE = {"score": 20, "locked": False, "screen": "on"}


async def mark_online(redis: Redis, user_id: str, device_id: str) -> None:
    """A device's WebSocket connected → it counts as online even before it
    reports presence. Doesn't clobber a real (higher-fidelity) observation."""
    key = redis_keys.activity(user_id, device_id)
    if await redis.get(key) is None:
        await redis.set(key, json.dumps(_CONNECTED_BASELINE), ex=redis_keys.ACTIVITY_TTL)
    else:
        await redis.expire(key, redis_keys.ACTIVITY_TTL)
    await select_active(redis, user_id)


async def refresh_online(redis: Redis, user_id: str, device_id: str) -> None:
    """Keep a connected device's presence from expiring while the socket lives."""
    await redis.expire(redis_keys.activity(user_id, device_id), redis_keys.ACTIVITY_TTL)


async def mark_offline(redis: Redis, user_id: str, device_id: str) -> None:
    await redis.delete(redis_keys.activity(user_id, device_id))
    await redis.delete(redis_keys.presence(user_id, device_id))
    await select_active(redis, user_id)


async def record_observation(
    redis: Redis, user_id: str, device_id: str, obs: Observation
) -> None:
    score = compute_activity_score(obs)
    await redis.set(
        redis_keys.presence(user_id, device_id),
        obs.model_dump_json(),
        ex=redis_keys.PRESENCE_TTL,
    )
    await redis.set(
        redis_keys.activity(user_id, device_id),
        json.dumps({"score": score, "locked": obs.locked, "screen": obs.screen}),
        ex=redis_keys.ACTIVITY_TTL,
    )
    await select_active(redis, user_id)


async def _gather(redis: Redis, user_id: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    async for key in redis.scan_iter(match=redis_keys.activity_pattern(user_id)):
        raw = await redis.get(key)
        if raw is None:
            continue
        device_id = key.split(":")[-1]
        out[device_id] = json.loads(raw)
    return out


async def select_active(redis: Redis, user_id: str) -> PresenceSnapshot:
    """Recompute primary/secondary applying hysteresis; persist active:{user}."""
    devices = await _gather(redis, user_id)
    active_key = redis_keys.active(user_id)

    if not devices:
        await redis.delete(active_key)
        return PresenceSnapshot()

    now_ms = int(time.time() * 1000)
    best = max(devices, key=lambda d: (devices[d]["score"], d))

    prev_raw = await redis.get(active_key)
    prev = json.loads(prev_raw) if prev_raw else None
    current = prev["primary"] if prev else None

    if current is None or current not in devices:
        primary, since = best, now_ms
    else:
        cur = devices[current]
        if cur.get("locked") or cur.get("screen") == "off":
            primary, since = best, now_ms  # immediate switch exception (§18)
        elif best != current:
            held = (now_ms - prev["since"]) >= MIN_HOLD_MS
            beats = devices[best]["score"] >= cur["score"] + SWITCH_THRESHOLD
            if beats and held:
                primary, since = best, now_ms
            else:
                primary, since = current, prev["since"]
        else:
            primary, since = current, prev["since"]

    await redis.set(active_key, json.dumps({"primary": primary, "since": since}),
                    ex=redis_keys.ACTIVE_TTL)
    return _snapshot(devices, primary)


def _snapshot(devices: dict[str, dict], primary: str) -> PresenceSnapshot:
    def out(dev: str) -> ActiveDeviceOut:
        score = devices[dev]["score"]
        return ActiveDeviceOut(
            device_id=dev, score=score, confidence=confidence_from_score(score)
        )

    others = sorted(
        (d for d in devices if d != primary),
        key=lambda d: devices[d]["score"],
        reverse=True,
    )
    return PresenceSnapshot(primary=out(primary), secondary=[out(d) for d in others])


async def get_snapshot(redis: Redis, user_id: str) -> PresenceSnapshot:
    devices = await _gather(redis, user_id)
    if not devices:
        return PresenceSnapshot()
    prev_raw = await redis.get(redis_keys.active(user_id))
    primary = json.loads(prev_raw)["primary"] if prev_raw else None
    if primary is None or primary not in devices:
        primary = max(devices, key=lambda d: (devices[d]["score"], d))
    return _snapshot(devices, primary)


async def ordered_device_ids(redis: Redis, user_id: str) -> list[str]:
    """Primary first, then secondary by descending score — for routing."""
    snap = await get_snapshot(redis, user_id)
    if snap.primary is None:
        return []
    return [snap.primary.device_id, *(d.device_id for d in snap.secondary)]
