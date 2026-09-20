"""Notification API: create, idempotency, scopes, TTL, isolation (§40, §46, §62)."""

from datetime import UTC, datetime

import pytest

from app.auth.scopes import (
    NOTIFICATION_BROADCAST,
    NOTIFICATION_SEND,
    NOTIFICATION_TARGET_DEVICE,
)


@pytest.fixture
async def owner(create_user, client):
    """A user_id plus their login headers plus a helper to mint agent headers."""
    user_id = await create_user("owner@example.com")
    login = await client.post(
        "/api/v1/auth/login", json={"email": "owner@example.com", "password": "pw-secret-123"}
    )
    user_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    return user_id, user_headers


async def _agent_headers(make_agent, user_id, scopes) -> dict[str, str]:
    _, token = await make_agent(user_id, scopes)
    return {"Authorization": f"Bearer {token}"}


async def test_create_notification(client, owner, make_agent):
    user_id, _ = owner
    h = await _agent_headers(make_agent, user_id, [NOTIFICATION_SEND])
    resp = await client.post(
        "/api/v1/notifications", headers=h, json={"title": "CI", "message": "done"}
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["id"].startswith("msg_")
    assert body["status"] in {"queued", "routed", "sent"}


async def test_create_requires_send_scope(client, owner, make_agent):
    user_id, _ = owner
    # agent without notification:send
    h = await _agent_headers(make_agent, user_id, ["notification:read"])
    resp = await client.post("/api/v1/notifications", headers=h, json={"message": "x"})
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "insufficient_scope"


async def test_all_devices_requires_broadcast(client, owner, make_agent):
    user_id, _ = owner
    h = await _agent_headers(make_agent, user_id, [NOTIFICATION_SEND])
    resp = await client.post(
        "/api/v1/notifications", headers=h,
        json={"message": "x", "routing": {"mode": "all_devices"}},
    )
    assert resp.status_code == 403

    h2 = await _agent_headers(make_agent, user_id, [NOTIFICATION_SEND, NOTIFICATION_BROADCAST])
    resp2 = await client.post(
        "/api/v1/notifications", headers=h2,
        json={"message": "x", "routing": {"mode": "all_devices"}},
    )
    assert resp2.status_code == 201


async def test_specific_device_requires_target_scope(client, owner, make_agent, make_device):
    user_id, _ = owner
    dev_id, _ = await make_device(user_id)
    h = await _agent_headers(make_agent, user_id, [NOTIFICATION_SEND, NOTIFICATION_TARGET_DEVICE])
    resp = await client.post(
        "/api/v1/notifications", headers=h,
        json={"message": "x", "routing": {"mode": "specific_device", "device_id": dev_id}},
    )
    assert resp.status_code == 201


async def test_idempotency_key(client, owner, make_agent):
    user_id, _ = owner
    h = {**await _agent_headers(make_agent, user_id, [NOTIFICATION_SEND]),
         "Idempotency-Key": "deploy-42"}
    r1 = await client.post("/api/v1/notifications", headers=h, json={"message": "once"})
    r2 = await client.post("/api/v1/notifications", headers=h, json={"message": "once"})
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]


async def test_ttl_defaults_by_priority(client, owner, make_agent):
    user_id, user_headers = owner
    h = await _agent_headers(make_agent, user_id, [NOTIFICATION_SEND])
    low = await client.post(
        "/api/v1/notifications", headers=h, json={"message": "l", "priority": "low"}
    )
    normal = await client.post(
        "/api/v1/notifications", headers=h, json={"message": "n", "priority": "normal"}
    )
    low_exp = await client.get(f"/api/v1/notifications/{low.json()['id']}", headers=user_headers)
    normal_exp = await client.get(
        f"/api/v1/notifications/{normal.json()['id']}", headers=user_headers
    )
    now = datetime.now(UTC)

    def _aware(iso: str) -> datetime:
        dt = datetime.fromisoformat(iso)
        # SQLite (test backend) drops tzinfo; Postgres timestamptz preserves it.
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)

    low_dt = _aware(low_exp.json()["expires_at"])
    normal_dt = _aware(normal_exp.json()["expires_at"])
    assert (low_dt - now).total_seconds() < 2 * 3600  # low = 30 min
    assert (normal_dt - now).total_seconds() > 12 * 3600  # normal = 24 h


async def test_invalid_priority_rejected(client, owner, make_agent):
    user_id, _ = owner
    h = await _agent_headers(make_agent, user_id, [NOTIFICATION_SEND])
    resp = await client.post(
        "/api/v1/notifications", headers=h, json={"message": "x", "priority": "urgent"}
    )
    assert resp.status_code == 400


async def test_list_and_read(client, owner, make_agent):
    user_id, user_headers = owner
    h = await _agent_headers(make_agent, user_id, [NOTIFICATION_SEND])
    created = await client.post("/api/v1/notifications", headers=h, json={"message": "hi"})
    nid = created.json()["id"]

    listing = await client.get("/api/v1/notifications", headers=user_headers)
    assert nid in {n["id"] for n in listing.json()}

    read = await client.post(f"/api/v1/notifications/{nid}/read", headers=user_headers)
    assert read.status_code == 200
    got = await client.get(f"/api/v1/notifications/{nid}", headers=user_headers)
    assert got.json()["read_at"] is not None


async def test_notifications_isolated_between_users(client, owner, make_agent, auth_headers):
    user_id, _ = owner
    h = await _agent_headers(make_agent, user_id, [NOTIFICATION_SEND])
    created = await client.post("/api/v1/notifications", headers=h, json={"message": "secret"})
    nid = created.json()["id"]

    other = await auth_headers("intruder@example.com")
    resp = await client.get(f"/api/v1/notifications/{nid}", headers=other)
    assert resp.status_code == 404
