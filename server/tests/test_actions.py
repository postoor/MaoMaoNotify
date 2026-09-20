"""Actions: create validation, first-response-wins, action_resolved broadcast,
webhook signatures + registration (§42–44, §66)."""

import httpx

from app.auth.scopes import NOTIFICATION_SEND
from app.models.agent import AgentWebhook
from app.notifications.webhooks import send_event, sign, verify
from app.websocket.manager import manager


class FakeWS:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def accept(self) -> None: ...

    async def send_json(self, data: dict) -> None:
        self.sent.append(data)


async def _owner(create_user, client):
    user_id = await create_user("owner@example.com")
    login = await client.post(
        "/api/v1/auth/login", json={"email": "owner@example.com", "password": "pw-secret-123"}
    )
    return user_id, {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _agent(make_agent, user_id):
    _, token = await make_agent(user_id, [NOTIFICATION_SEND])
    return {"Authorization": f"Bearer {token}"}


# --- webhook signing (pure) ---

def test_sign_and_verify():
    sig = sign("secret", "1000", b"body")
    assert verify("secret", "1000", b"body", f"sha256={sig}")
    assert not verify("secret", "1000", b"tampered", f"sha256={sig}")
    assert not verify("wrong", "1000", b"body", f"sha256={sig}")


async def test_send_event_signs_request():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = request.headers
        captured["body"] = request.content
        return httpx.Response(200)

    wh = AgentWebhook(agent_id="a", url="http://sink/hook", secret="s3cr3t", events=[])
    await send_event(
        [wh], "notification.responded", {"notification_id": "msg_1"},
        transport=httpx.MockTransport(handler),
    )
    ts = captured["headers"]["X-MaoMao-Timestamp"]
    sig = captured["headers"]["X-MaoMao-Signature"]
    assert captured["headers"]["X-MaoMao-Event"] == "notification.responded"
    assert verify("s3cr3t", ts, captured["body"], sig)


# --- create validation ---

async def test_invalid_action_rejected(client, create_user, make_agent):
    user_id, _ = await _owner(create_user, client)
    h = await _agent(make_agent, user_id)
    resp = await client.post(
        "/api/v1/notifications", headers=h,
        json={"message": "x", "actions": [{"id": "a", "type": "nope"}]},
    )
    assert resp.status_code == 400


# --- first-response-wins + broadcast ---

async def test_first_response_wins_and_broadcast(client, create_user, make_agent, make_device):
    user_id, _ = await _owner(create_user, client)
    h = await _agent(make_agent, user_id)
    dev1, tok1 = await make_device(user_id, "macos")
    dev2, tok2 = await make_device(user_id, "android")
    ws2 = FakeWS()
    manager._conns[dev1] = FakeWS()
    manager._conns[dev2] = ws2

    created = await client.post(
        "/api/v1/notifications", headers=h,
        json={"title": "Deploy", "message": "failed",
              "actions": [{"id": "retry", "type": "button", "label": "Retry"},
                          {"id": "cancel", "type": "button", "label": "Cancel"}]},
    )
    nid = created.json()["id"]

    # device 1 responds first → wins
    r1 = await client.post(
        f"/api/v1/notifications/{nid}/responses",
        headers={"Authorization": f"Bearer {tok1}"}, json={"action_id": "retry"},
    )
    assert r1.status_code == 201
    assert r1.json()["action_id"] == "retry"

    # device 2 got told to disable its buttons
    assert any(m["event"] == "action_resolved" and m["notification_id"] == nid for m in ws2.sent)

    # device 2 responds late → 409
    r2 = await client.post(
        f"/api/v1/notifications/{nid}/responses",
        headers={"Authorization": f"Bearer {tok2}"}, json={"action_id": "cancel"},
    )
    assert r2.status_code == 409
    assert r2.json()["error"]["code"] == "action_already_resolved"


async def test_unknown_action_rejected(client, create_user, make_agent, make_device):
    user_id, _ = await _owner(create_user, client)
    h = await _agent(make_agent, user_id)
    _dev, tok = await make_device(user_id)
    created = await client.post(
        "/api/v1/notifications", headers=h,
        json={"message": "hi", "actions": [{"id": "ok", "type": "button", "label": "OK"}]},
    )
    nid = created.json()["id"]
    resp = await client.post(
        f"/api/v1/notifications/{nid}/responses",
        headers={"Authorization": f"Bearer {tok}"}, json={"action_id": "bogus"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "unknown_action"


async def test_text_input_response_value(client, create_user, make_agent, make_device):
    user_id, _ = await _owner(create_user, client)
    h = await _agent(make_agent, user_id)
    _dev, tok = await make_device(user_id)
    created = await client.post(
        "/api/v1/notifications", headers=h,
        json={"message": "version?", "correlation_id": "deploy_9",
              "actions": [{"id": "version", "type": "text_input", "label": "Version"}]},
    )
    nid = created.json()["id"]
    resp = await client.post(
        f"/api/v1/notifications/{nid}/responses",
        headers={"Authorization": f"Bearer {tok}"},
        json={"action_id": "version", "value": "v1.4.2"},
    )
    assert resp.status_code == 201
    assert resp.json()["value"] == "v1.4.2"
    assert resp.json()["correlation_id"] == "deploy_9"


# --- webhook registration ---

async def test_register_webhook(client, create_user, make_agent):
    _user_id, user_headers = await _owner(create_user, client)
    created = await client.post("/api/v1/agents", headers=user_headers, json={"name": "ci"})
    agent_id = created.json()["id"]

    reg = await client.post(
        f"/api/v1/agents/{agent_id}/webhooks", headers=user_headers,
        json={"url": "https://example.com/hook", "events": ["notification.responded"]},
    )
    assert reg.status_code == 201
    assert reg.json()["secret"]  # returned once

    listing = await client.get(f"/api/v1/agents/{agent_id}/webhooks", headers=user_headers)
    assert len(listing.json()) == 1
    assert "secret" not in listing.json()[0]
