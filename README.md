# MaoMaoNotify

Cross-platform AI Agent notification platform. AI agents send text / voice /
interactive / question / reply-able notifications to a user; the server decides
which of the user's devices is most likely active and routes accordingly, under
the rule **User Policy > Device Policy > Agent Request**.

First-stage clients: macOS (Apple Silicon), Linux Desktop, Android.
Backend is multi-user from day one.

## Repository layout

```
MaoMaoNotify/
├── server/            FastAPI backend (Python 3.13, async, uv-managed)
├── client/            Flutter app (Android / macOS / Linux, single repo)
├── web/               Web admin console
├── docs/              Architecture & specification
├── docker/            Provider containers (piper, kokoro)
├── scripts/           Dev / ops helper scripts
├── docker-compose.yml server + postgres + redis + minio (+ optional tts)
├── .env.example       Configuration template (copy to .env)
└── README.md
```

## Quick start (skeleton)

```bash
cp .env.example .env          # then fill in secrets
docker compose up -d          # postgres, redis, minio, server
```

Backend local dev (uv):

```bash
cd server
uv sync
uv run uvicorn app.main:app --reload
```

Health check: `GET http://localhost:8000/health`

## Status

**Phase 1–3 complete.** Backend (Phase 1–2): auth (JWT + rotating refresh),
multi-user isolation, device registry + pairing, agent registry + scopes;
activity scoring, presence + active-device selection, routing engine,
notification API (idempotency, TTL, priority), delivery lifecycle + fallback,
WebSocket gateway, agent presence view. 53 server tests, Alembic migrations,
Docker Compose. Desktop client (Phase 3, Linux-first): Flutter app with
api/auth/websocket/presence/tts/notification layers + setup/home UI; 22 client
tests, analyze clean, Linux bundle builds, live E2E verified. Android (Phase 4):
IMU motion classification, platform-native TTS/notifications, Voice Alerts Mode
foreground service, FCM wake→fetch scaffolding; 42 client tests, APK builds,
and live-verified on a real Galaxy S21 (notification + native TTS + IMU
presence + Voice Alerts foreground service). Server TTS (Phase 5): TTSProvider
abstraction (Edge/Piper/Kokoro, Edge default), audio synthesis → MinIO →
presigned URL, client_tts fallback; live-verified end-to-end (real Edge-TTS mp3
stored and downloaded). Agent Audio (Phase 6): presigned-PUT upload → MinIO →
audio_id → signed URL, with client playback (desktop mpv/ffplay, Android
MediaPlayer); live-verified byte-identical round-trip + playback. Actions
(Phase 7): button / text_input, first-response-wins with action_resolved
broadcast, correlation_id, HMAC-signed agent webhooks; interactive client UI;
live-verified (409 on second response + verified webhook signature). Web Admin
(Phase 8): build-free vanilla-JS SPA served at `/admin` — devices, agents +
webhooks, preferences/quiet-hours, voice settings, notification history, admin
server-TTS provider + user management. **All 8 phases complete and verified.**

Also: ACK-timeout delivery fallback (§53) is wired to a timer; a production
image (`docker/Dockerfile.prod` + `docker-compose.prod.yml`, auto-migrates on
start, bakes the web admin) is built and verified. See `docs/architecture.md`
for the design and `docs/deployment.md` for deploying.
