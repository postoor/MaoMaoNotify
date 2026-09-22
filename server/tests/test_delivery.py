"""Delivery dispatch, ACK lifecycle, fallback escalation, WS handler (§49–53)."""

from sqlalchemy import select

from app.auth.scopes import NOTIFICATION_SEND
from app.models.device import Device
from app.models.notification import NotificationDelivery
from app.notifications import constants as c
from app.notifications.delivery import apply_ack, run_fallback, schedule_fallback
from app.notifications.schemas import NotificationCreate
from app.notifications.service import create_notification
from app.presence import manager as pm
from app.presence.schemas import Observation
from app.websocket.gateway import handle_message
from app.websocket.manager import manager


class FakeWS:
    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.accepted = False

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, data: dict) -> None:
        self.sent.append(data)


async def _mk_user(sessionmaker) -> str:
    from app.models.user import User

    async with sessionmaker() as s:
        u = User(email=f"{id(object()):x}@t.com")
        s.add(u)
        await s.commit()
        return u.id


async def _mk_device(sessionmaker, user_id, platform="macos") -> str:
    async with sessionmaker() as s:
        d = Device(user_id=user_id, platform=platform)
        s.add(d)
        await s.commit()
        return d.id


async def _deliveries(session, nid):
    return (
        await session.execute(
            select(NotificationDelivery)
            .where(NotificationDelivery.notification_id == nid)
            .order_by(NotificationDelivery.order_index)
        )
    ).scalars().all()


async def test_dispatch_to_online_device(sessionmaker, redis):
    manager._conns.clear()
    user_id = await _mk_user(sessionmaker)
    dev_id = await _mk_device(sessionmaker, user_id)
    ws = FakeWS()
    manager._conns[dev_id] = ws  # online

    async with sessionmaker() as session:
        n = await create_notification(
            session, redis, user_id=user_id, agent_id=None,
            scopes=[NOTIFICATION_SEND], body=NotificationCreate(message="hi"),
        )
        assert n.status == c.STATUS_SENT
        deliveries = await _deliveries(session, n.id)
        assert len(deliveries) == 1
        assert deliveries[0].status == c.DELIVERY_SENT
    assert len(ws.sent) == 1
    assert ws.sent[0]["event"] == "notification"
    assert ws.sent[0]["notification"]["id"] == n.id
    # created_at is included so the client can show when it was received (§62).
    assert ws.sent[0]["notification"]["created_at"] is not None


async def test_signed_voice_mints_fresh_url_from_audio_id(sessionmaker):
    from app.models.audio import AudioAsset
    from app.notifications.delivery import signed_voice
    from app.storage.memory import InMemoryStorage

    user_id = await _mk_user(sessionmaker)
    storage = InMemoryStorage()
    async with sessionmaker() as s:
        asset = AudioAsset(
            user_id=user_id, source="server_tts", content_type="audio/mpeg",
            size=3, storage_key="audio/x.mp3",
        )
        s.add(asset)
        await s.commit()

        # audio_id → a freshly-signed URL is attached
        voice = await signed_voice({"source": "server_tts", "audio_id": asset.id}, s, storage)
        assert voice["audio_url"].startswith("memory://audio/x.mp3")

        # no audio asset (client_tts) → unchanged
        assert await signed_voice({"source": "client_tts"}, s, storage) == {"source": "client_tts"}

        # no storage → no URL minted
        assert "audio_url" not in await signed_voice({"audio_id": asset.id}, s, None)


async def test_offline_device_stays_routed(sessionmaker, redis):
    manager._conns.clear()
    user_id = await _mk_user(sessionmaker)
    await _mk_device(sessionmaker, user_id)  # no WS registered → offline

    async with sessionmaker() as session:
        n = await create_notification(
            session, redis, user_id=user_id, agent_id=None,
            scopes=[NOTIFICATION_SEND], body=NotificationCreate(message="hi"),
        )
        assert n.status == c.STATUS_ROUTED
        deliveries = await _deliveries(session, n.id)
        assert deliveries[0].status == c.DELIVERY_ROUTED


async def test_apply_ack_advances_state(sessionmaker, redis):
    manager._conns.clear()
    user_id = await _mk_user(sessionmaker)
    dev_id = await _mk_device(sessionmaker, user_id)
    manager._conns[dev_id] = FakeWS()

    async with sessionmaker() as session:
        n = await create_notification(
            session, redis, user_id=user_id, agent_id=None,
            scopes=[NOTIFICATION_SEND], body=NotificationCreate(message="hi"),
        )
        await apply_ack(session, dev_id, n.id, c.DELIVERY_DELIVERED)
        deliveries = await _deliveries(session, n.id)
        assert deliveries[0].status == c.DELIVERY_DELIVERED
        assert deliveries[0].delivered_at is not None
        await session.refresh(n)
        assert n.status == c.DELIVERY_DELIVERED


async def test_fallback_escalates_to_secondary(sessionmaker, redis):
    manager._conns.clear()
    user_id = await _mk_user(sessionmaker)
    primary = await _mk_device(sessionmaker, user_id, "macos")
    secondary = await _mk_device(sessionmaker, user_id, "android")
    ws_primary, ws_secondary = FakeWS(), FakeWS()
    manager._conns[primary] = ws_primary
    manager._conns[secondary] = ws_secondary

    # presence: primary higher score than secondary
    await pm.record_observation(
        redis, user_id, primary, Observation(screen="on", locked=False, last_interaction_ms=5_000)
    )
    await pm.record_observation(
        redis, user_id, secondary,
        Observation(screen="on", locked=False, last_interaction_ms=240_000),
    )

    async with sessionmaker() as session:
        n = await create_notification(
            session, redis, user_id=user_id, agent_id=None,
            scopes=[NOTIFICATION_SEND], body=NotificationCreate(message="hi"),
        )
        # active_with_fallback → only primary sent
        assert len(ws_primary.sent) == 1
        assert len(ws_secondary.sent) == 0

        # primary never ACKs → escalate
        escalated = await run_fallback(session, n.id)
        assert escalated is True
        deliveries = await _deliveries(session, n.id)
        by_dev = {d.device_id: d.status for d in deliveries}
        assert by_dev[primary] == c.DELIVERY_FALLBACK_CANCELLED
        assert by_dev[secondary] == c.DELIVERY_SENT
        assert len(ws_secondary.sent) == 1


async def test_fallback_timer_escalates(sessionmaker, redis):
    manager._conns.clear()
    user_id = await _mk_user(sessionmaker)
    primary = await _mk_device(sessionmaker, user_id, "macos")
    secondary = await _mk_device(sessionmaker, user_id, "android")
    manager._conns[primary] = FakeWS()
    ws_secondary = FakeWS()
    manager._conns[secondary] = ws_secondary
    await pm.record_observation(
        redis, user_id, primary, Observation(screen="on", locked=False, last_interaction_ms=5_000)
    )
    await pm.record_observation(
        redis, user_id, secondary,
        Observation(screen="on", locked=False, last_interaction_ms=240_000),
    )

    async with sessionmaker() as session:
        n = await create_notification(
            session, redis, user_id=user_id, agent_id=None,
            scopes=[NOTIFICATION_SEND], body=NotificationCreate(message="hi"),
        )
        nid = n.id

    # fire the timer with zero delay and the test session factory
    await schedule_fallback(nid, 0.0, session_factory=sessionmaker)

    async with sessionmaker() as session:
        deliveries = await _deliveries(session, nid)
        by_dev = {d.device_id: d.status for d in deliveries}
    assert by_dev[primary] == c.DELIVERY_FALLBACK_CANCELLED
    assert by_dev[secondary] == c.DELIVERY_SENT
    assert len(ws_secondary.sent) == 1


async def test_fallback_noop_when_delivered(sessionmaker, redis):
    manager._conns.clear()
    user_id = await _mk_user(sessionmaker)
    dev_id = await _mk_device(sessionmaker, user_id)
    manager._conns[dev_id] = FakeWS()

    async with sessionmaker() as session:
        n = await create_notification(
            session, redis, user_id=user_id, agent_id=None,
            scopes=[NOTIFICATION_SEND], body=NotificationCreate(message="hi"),
        )
        await apply_ack(session, dev_id, n.id, c.DELIVERY_DELIVERED)
        assert await run_fallback(session, n.id) is False


async def test_ws_handle_ack_and_read(sessionmaker, redis):
    manager._conns.clear()
    user_id = await _mk_user(sessionmaker)
    dev_id = await _mk_device(sessionmaker, user_id)
    manager._conns[dev_id] = FakeWS()

    async with sessionmaker() as session:
        n = await create_notification(
            session, redis, user_id=user_id, agent_id=None,
            scopes=[NOTIFICATION_SEND], body=NotificationCreate(message="hi"),
        )
        device = await session.get(Device, dev_id)
        await handle_message(
            session, device,
            {"type": "ack", "notification_id": n.id, "status": c.DELIVERY_DISPLAYED},
        )
        await handle_message(session, device, {"type": "read", "notification_id": n.id})

        deliveries = await _deliveries(session, n.id)
        assert deliveries[0].status == c.DELIVERY_DISPLAYED
        await session.refresh(n)
        assert n.read_at is not None
