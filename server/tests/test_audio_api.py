"""GET /audio/{id} returns a signed URL for the owner only (§35, §61)."""

from app.models.audio import AudioAsset


async def _make_asset(sessionmaker, user_id: str) -> str:
    async with sessionmaker() as s:
        a = AudioAsset(
            user_id=user_id, source="server_tts", provider="edge_tts",
            content_type="audio/mpeg", size=123, storage_key="audio/x.mp3",
        )
        s.add(a)
        await s.commit()
        return a.id


async def test_owner_gets_signed_url(client, create_user, sessionmaker):
    user_id = await create_user("owner@example.com")
    login = await client.post(
        "/api/v1/auth/login", json={"email": "owner@example.com", "password": "pw-secret-123"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    audio_id = await _make_asset(sessionmaker, user_id)

    resp = await client.get(f"/api/v1/audio/{audio_id}", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == audio_id
    assert body["content_type"] == "audio/mpeg"
    assert body["url"].startswith("memory://audio/x.mp3")


async def test_other_user_cannot_access(client, create_user, sessionmaker, auth_headers):
    owner_id = await create_user("owner@example.com")
    audio_id = await _make_asset(sessionmaker, owner_id)
    intruder = await auth_headers("intruder@example.com")
    resp = await client.get(f"/api/v1/audio/{audio_id}", headers=intruder)
    assert resp.status_code == 404
