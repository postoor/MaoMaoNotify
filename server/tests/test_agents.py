"""Agent registry + scopes (§8)."""

from app.auth.scopes import (
    ACTION_RECEIVE,
    NOTIFICATION_BROADCAST,
    NOTIFICATION_READ,
    NOTIFICATION_SEND,
    NOTIFICATION_TARGET_DEVICE,
    has_scopes,
)


async def test_agent_default_scopes_exclude_privileged(client, auth_headers):
    headers = await auth_headers("a@example.com")
    resp = await client.post("/api/v1/agents", headers=headers, json={"name": "claude-code"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["token"]  # returned once
    scopes = set(body["scopes"])
    assert scopes == {NOTIFICATION_SEND, NOTIFICATION_READ, ACTION_RECEIVE}
    assert NOTIFICATION_BROADCAST not in scopes
    assert NOTIFICATION_TARGET_DEVICE not in scopes


async def test_agent_explicit_scopes_can_grant_broadcast(client, auth_headers):
    headers = await auth_headers("a@example.com")
    resp = await client.post(
        "/api/v1/agents",
        headers=headers,
        json={"name": "broadcaster", "scopes": [NOTIFICATION_SEND, NOTIFICATION_BROADCAST]},
    )
    assert resp.status_code == 201
    assert NOTIFICATION_BROADCAST in resp.json()["scopes"]


async def test_agent_unknown_scope_rejected(client, auth_headers):
    headers = await auth_headers("a@example.com")
    resp = await client.post(
        "/api/v1/agents",
        headers=headers,
        json={"name": "bad", "scopes": ["notification:nuke"]},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_scope"


def test_has_scopes():
    assert has_scopes({NOTIFICATION_SEND, NOTIFICATION_READ}, {NOTIFICATION_SEND})
    assert not has_scopes({NOTIFICATION_SEND}, {NOTIFICATION_BROADCAST})
