"""Admin: user management, TTS settings, runtime override, device prefs (§29, §70)."""

from app.core.config import settings
from app.core.runtime import effective_tts_provider, set_setting
from app.models.notification import Notification
from app.storage.memory import InMemoryStorage
from app.tts.base import AudioResult, TTSProvider
from app.tts.synthesizer import VoiceSynthesizer


async def _admin(create_user, client) -> dict[str, str]:
    await create_user("admin@example.com", role="admin")
    login = await client.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": "pw-secret-123"}
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def test_non_admin_forbidden(client, auth_headers):
    user = await auth_headers("plain@example.com")
    resp = await client.get("/api/v1/admin/users", headers=user)
    assert resp.status_code == 403


async def test_user_crud(client, create_user):
    admin = await _admin(create_user, client)

    created = await client.post(
        "/api/v1/admin/users", headers=admin,
        json={"email": "new@example.com", "password": "pw123456", "role": "user"},
    )
    assert created.status_code == 201
    new_id = created.json()["id"]

    dup = await client.post(
        "/api/v1/admin/users", headers=admin,
        json={"email": "new@example.com", "password": "pw123456"},
    )
    assert dup.status_code == 409

    listing = await client.get("/api/v1/admin/users", headers=admin)
    assert "new@example.com" in {u["email"] for u in listing.json()}

    deleted = await client.delete(f"/api/v1/admin/users/{new_id}", headers=admin)
    assert deleted.status_code == 204


async def test_cannot_delete_self(client, create_user):
    admin = await _admin(create_user, client)
    me = await client.get("/api/v1/me", headers=admin)
    resp = await client.delete(f"/api/v1/admin/users/{me.json()['id']}", headers=admin)
    assert resp.status_code == 400


async def test_tts_settings_roundtrip(client, create_user):
    admin = await _admin(create_user, client)
    got = await client.get("/api/v1/admin/settings/tts", headers=admin)
    assert got.json()["provider"] == "edge_tts"
    assert "kokoro" in got.json()["available"]

    patched = await client.patch(
        "/api/v1/admin/settings/tts", headers=admin, json={"provider": "kokoro"}
    )
    assert patched.status_code == 200
    assert patched.json()["provider"] == "kokoro"

    again = await client.get("/api/v1/admin/settings/tts", headers=admin)
    assert again.json()["provider"] == "kokoro"

    bad = await client.patch(
        "/api/v1/admin/settings/tts", headers=admin, json={"provider": "bogus"}
    )
    assert bad.status_code == 400


async def test_effective_provider_override(sessionmaker):
    async with sessionmaker() as s:
        assert await effective_tts_provider(s, settings) == settings.tts_provider
        await set_setting(s, "tts_provider", "kokoro")
        assert await effective_tts_provider(s, settings) == "kokoro"


class _RecordingProvider(TTSProvider):
    name = "rec"

    def __init__(self, requested: str):
        self.requested = requested

    async def synthesize(self, text, language=None, voice=None, options=None):
        return AudioResult(b"x", "audio/mpeg", voice, language, self.requested)


async def test_synth_uses_runtime_default(sessionmaker, create_user):
    from datetime import UTC, datetime, timedelta

    user_id = await create_user("u@example.com")
    seen = {}

    def factory(name):
        seen["name"] = name
        return _RecordingProvider(name)

    synth = VoiceSynthesizer(
        InMemoryStorage(), settings, provider_factory=factory, default_provider="kokoro"
    )
    async with sessionmaker() as s:
        n = Notification(
            user_id=user_id, type="voice", message="hi",
            voice={"source": "server_tts"},  # no explicit provider → uses override
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        s.add(n)
        await s.flush()
        await synth.apply(s, n, "hi")
    assert seen["name"] == "kokoro"


async def test_device_preferences(client, create_user, make_device, auth_headers):
    user_id = await create_user("owner@example.com")
    login = await client.post(
        "/api/v1/auth/login", json={"email": "owner@example.com", "password": "pw-secret-123"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    dev_id, _ = await make_device(user_id)

    got = await client.get(f"/api/v1/devices/{dev_id}/preferences", headers=headers)
    assert got.status_code == 200
    assert got.json()["voice_policy"] == {}

    patched = await client.patch(
        f"/api/v1/devices/{dev_id}/preferences", headers=headers,
        json={"voice_policy": {"mode": "active_only", "headphones_only": True}},
    )
    assert patched.status_code == 200
    assert patched.json()["voice_policy"]["headphones_only"] is True

    intruder = await auth_headers("intruder@example.com")
    denied = await client.get(f"/api/v1/devices/{dev_id}/preferences", headers=intruder)
    assert denied.status_code == 404
