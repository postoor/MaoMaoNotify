"""Agent audio: upload request, resolution into a notification, errors (§34)."""

import pytest

from app.auth.scopes import NOTIFICATION_SEND
from app.models.audio import AudioAsset


@pytest.fixture
async def owner(create_user, client):
    user_id = await create_user("owner@example.com")
    login = await client.post(
        "/api/v1/auth/login", json={"email": "owner@example.com", "password": "pw-secret-123"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    return user_id, headers


async def _agent(make_agent, user_id, scopes) -> dict[str, str]:
    _, token = await make_agent(user_id, scopes)
    return {"Authorization": f"Bearer {token}"}


async def _storage_key(sessionmaker, audio_id: str) -> str:
    async with sessionmaker() as s:
        return (await s.get(AudioAsset, audio_id)).storage_key


async def test_upload_requires_send_scope(client, owner, make_agent):
    user_id, _ = owner
    h = await _agent(make_agent, user_id, ["notification:read"])
    resp = await client.post("/api/v1/audio/uploads", headers=h, json={"content_type": "audio/mpeg"})
    assert resp.status_code == 403


async def test_request_upload_returns_presigned_put(client, owner, make_agent):
    user_id, _ = owner
    h = await _agent(make_agent, user_id, [NOTIFICATION_SEND])
    resp = await client.post("/api/v1/audio/uploads", headers=h, json={"content_type": "audio/mpeg"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["audio_id"].startswith("audio_")
    assert body["method"] == "PUT"
    assert body["upload_url"].startswith("memory://put/")
    assert body["headers"]["Content-Type"] == "audio/mpeg"


async def test_full_agent_audio_flow(client, owner, make_agent, sessionmaker, storage):
    user_id, user_headers = owner
    h = await _agent(make_agent, user_id, [NOTIFICATION_SEND])

    up = await client.post("/api/v1/audio/uploads", headers=h, json={"content_type": "audio/mpeg"})
    audio_id = up.json()["audio_id"]
    key = await _storage_key(sessionmaker, audio_id)

    # simulate the agent PUTting the bytes to the presigned URL
    await storage.put(key, b"FAKE-AGENT-AUDIO-BYTES", "audio/mpeg")

    created = await client.post(
        "/api/v1/notifications", headers=h,
        json={"title": "Voice", "type": "voice",
              "voice": {"source": "agent_audio", "audio_id": audio_id}},
    )
    assert created.status_code == 201
    nid = created.json()["id"]

    detail = await client.get(f"/api/v1/notifications/{nid}", headers=user_headers)
    voice = detail.json()["voice"]
    assert voice["source"] == "agent_audio"
    assert voice["audio_url"].startswith("memory://")

    async with sessionmaker() as s:
        assert (await s.get(AudioAsset, audio_id)).size == len(b"FAKE-AGENT-AUDIO-BYTES")


async def test_agent_audio_not_uploaded_yet(client, owner, make_agent):
    user_id, _ = owner
    h = await _agent(make_agent, user_id, [NOTIFICATION_SEND])
    up = await client.post("/api/v1/audio/uploads", headers=h, json={"content_type": "audio/mpeg"})
    audio_id = up.json()["audio_id"]  # never uploaded

    resp = await client.post(
        "/api/v1/notifications", headers=h,
        json={"type": "voice", "voice": {"source": "agent_audio", "audio_id": audio_id}},
    )
    assert resp.status_code == 400
    assert "uploaded" in resp.json()["error"]["message"]


async def test_agent_audio_missing_id(client, owner, make_agent):
    user_id, _ = owner
    h = await _agent(make_agent, user_id, [NOTIFICATION_SEND])
    resp = await client.post(
        "/api/v1/notifications", headers=h,
        json={"type": "voice", "voice": {"source": "agent_audio"}},
    )
    assert resp.status_code == 400


async def test_agent_audio_other_users_asset(client, owner, make_agent, create_user, sessionmaker, storage):
    user_id, _ = owner
    # asset owned by a different user
    other_id = await create_user("other@example.com")
    async with sessionmaker() as s:
        asset = AudioAsset(user_id=other_id, source="agent_audio", content_type="audio/mpeg",
                           size=0, storage_key="audio/other.mp3")
        s.add(asset)
        await s.commit()
        other_audio_id = asset.id
    await storage.put("audio/other.mp3", b"x", "audio/mpeg")

    h = await _agent(make_agent, user_id, [NOTIFICATION_SEND])
    resp = await client.post(
        "/api/v1/notifications", headers=h,
        json={"type": "voice", "voice": {"source": "agent_audio", "audio_id": other_audio_id}},
    )
    assert resp.status_code == 400
    assert "not found" in resp.json()["error"]["message"]
