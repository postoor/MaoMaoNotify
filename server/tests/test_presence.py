"""Presence manager + active-device hysteresis (§17, §18, §81)."""

import json

from app.core import redis_keys
from app.presence import manager as pm
from app.presence.schemas import Observation

USER = "usr_test"
MAC = "dev_mac"
PHONE = "dev_phone"


def _active(**kw) -> Observation:
    return Observation(screen="on", locked=False, **kw)


async def test_single_device_is_primary(redis):
    await pm.record_observation(redis, USER, MAC, _active(last_interaction_ms=5_000))
    snap = await pm.get_snapshot(redis, USER)
    assert snap.primary.device_id == MAC
    assert snap.primary.score == 75
    assert snap.secondary == []


async def test_highest_score_wins_initially(redis):
    await pm.record_observation(redis, USER, MAC, _active(last_interaction_ms=5_000))  # 75
    await pm.record_observation(redis, USER, PHONE, _active(last_interaction_ms=240_000))  # 25
    snap = await pm.get_snapshot(redis, USER)
    assert snap.primary.device_id == MAC
    assert [d.device_id for d in snap.secondary] == [PHONE]


async def test_switch_blocked_within_hold(redis):
    # Mac becomes primary (fresh 'since'), then phone reports higher score.
    await pm.record_observation(redis, USER, MAC, _active(last_interaction_ms=5_000))  # 75
    await pm.record_observation(
        redis, USER, PHONE, _active(last_interaction_ms=3_000, motion="handheld")
    )  # 95
    snap = await pm.get_snapshot(redis, USER)
    assert snap.primary.device_id == MAC  # held despite phone scoring higher


async def test_switch_allowed_after_hold(redis):
    await pm.record_observation(redis, USER, MAC, _active(last_interaction_ms=5_000))
    await pm.record_observation(
        redis, USER, PHONE, _active(last_interaction_ms=3_000, motion="handheld")
    )
    # rewind the hold window so it has elapsed
    raw = json.loads(await redis.get(redis_keys.active(USER)))
    raw["since"] -= pm.MIN_HOLD_MS + 1_000
    await redis.set(redis_keys.active(USER), json.dumps(raw))

    await pm.select_active(redis, USER)
    snap = await pm.get_snapshot(redis, USER)
    assert snap.primary.device_id == PHONE  # §81: phone takes over once eligible


async def test_immediate_switch_when_primary_locked(redis):
    await pm.record_observation(redis, USER, MAC, _active(last_interaction_ms=5_000))
    # Mac now locks; phone is active and handheld
    await pm.record_observation(redis, USER, MAC, Observation(screen="on", locked=True))
    await pm.record_observation(
        redis, USER, PHONE, _active(last_interaction_ms=3_000, motion="handheld")
    )
    snap = await pm.get_snapshot(redis, USER)
    assert snap.primary.device_id == PHONE  # locked primary → immediate switch


async def test_mark_online_makes_device_present(redis):
    await pm.mark_online(redis, USER, MAC)
    snap = await pm.get_snapshot(redis, USER)
    assert snap.primary is not None
    assert snap.primary.device_id == MAC
    assert snap.primary.score >= 1  # online, not offline

    await pm.mark_offline(redis, USER, MAC)
    assert (await pm.get_snapshot(redis, USER)).primary is None


async def test_mark_online_does_not_clobber_real_score(redis):
    await pm.record_observation(redis, USER, MAC, _active(last_interaction_ms=5_000))  # 75
    await pm.mark_online(redis, USER, MAC)  # must not downgrade
    assert (await pm.get_snapshot(redis, USER)).primary.score == 75


async def test_ordered_device_ids(redis):
    await pm.record_observation(redis, USER, MAC, _active(last_interaction_ms=5_000))
    await pm.record_observation(redis, USER, PHONE, _active(last_interaction_ms=240_000))
    assert await pm.ordered_device_ids(redis, USER) == [MAC, PHONE]
