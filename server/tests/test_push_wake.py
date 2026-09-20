"""UnifiedPush wake: endpoint registration + waking offline Android (§56 alt)."""

from datetime import UTC, datetime, timedelta

import httpx

from app.models.device import Device
from app.models.notification import Notification, NotificationDelivery
from app.notifications import constants as c
from app.notifications.delivery import send_push_wakes
from app.websocket.manager import manager


async def test_register_push_endpoint(client, create_user, make_device, sessionmaker):
    user_id = await create_user("u@example.com")
    dev_id, tok = await make_device(user_id, "android")
    resp = await client.post(
        "/api/v1/devices/push-endpoint",
        headers={"Authorization": f"Bearer {tok}"},
        json={"endpoint": "http://ntfy.local/upABC?up=1"},
    )
    assert resp.status_code == 200
    async with sessionmaker() as s:
        assert (await s.get(Device, dev_id)).push_endpoint == "http://ntfy.local/upABC?up=1"


async def _device(session, user_id, platform, *, endpoint=None):
    d = Device(user_id=user_id, platform=platform, push_endpoint=endpoint)
    session.add(d)
    await session.flush()
    return d.id


async def test_send_push_wakes_only_offline_android_with_endpoint(sessionmaker):
    manager._conns.clear()
    async with sessionmaker() as s:
        from app.models.user import User
        u = User(email="w@example.com")
        s.add(u)
        await s.flush()
        uid = u.id

        android_off = await _device(s, uid, "android", endpoint="http://ntfy/up_off")
        android_on = await _device(s, uid, "android", endpoint="http://ntfy/up_on")
        mac_off = await _device(s, uid, "macos", endpoint="http://ntfy/up_mac")
        android_noep = await _device(s, uid, "android", endpoint=None)

        n = Notification(
            user_id=uid, type="text", message="hi",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        s.add(n)
        await s.flush()
        deliveries = []
        for i, dev in enumerate([android_off, android_on, mac_off, android_noep]):
            d = NotificationDelivery(
                notification_id=n.id, device_id=dev, status=c.DELIVERY_ROUTED, order_index=i,
            )
            s.add(d)
            deliveries.append(d)
        await s.commit()

        manager._conns[android_on] = object()  # online → must be skipped

        posted = []

        def handler(req: httpx.Request) -> httpx.Response:
            posted.append(str(req.url))
            return httpx.Response(200)

        sent = await send_push_wakes(s, n, deliveries, transport=httpx.MockTransport(handler))

    assert sent == 1
    assert posted == ["http://ntfy/up_off"]
