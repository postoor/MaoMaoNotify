# MaoMaoNotify — Architecture & Plan

Condensed from the v0.1 development specification. The full spec is the source
of truth; this file is the map.

## Core pipeline (§3)

```
Presence  →  Routing  →  Policy  →  Presentation
```

- **Presence** — infer which device the user is most likely on.
- **Routing** — decide which device(s) receive the notification.
- **Policy** — decide what the user allows.
- **Presentation** — text / client TTS / server TTS / agent audio.

**Invariant: User Policy > Device Policy > Agent Request.** Agents never bypass
user settings, never need a device ID, and normally target only a *user*; the
server chooses routing.

## Key design points

- **Multi-user** with full isolation of devices, agents, notifications,
  presence, preferences, and audio assets (§6).
- **Auth**: user email+password → JWT access (15–30m) + opaque refresh (30d);
  schema reserves OIDC/OAuth2/SSO (§7). Agents have their own tokens + scopes;
  `notification:broadcast` / `notification:target_device` are **not** default
  (§8).
- **Device pairing** via QR + one-time token (5 min, single use); device
  keypair, immutable `device_id` (§9–10).
- **Presence** is observation-only — the client never declares "active"; server
  computes `activity_score` (0–100) and picks primary/secondary devices with
  hysteresis (§12–18). Strict privacy: no keystrokes, coordinates, URLs, or raw
  sensor streams (§13).
- **Notifications**: types `text` / `voice` (voice source ∈ client_tts /
  server_tts / agent_audio). Priority low/normal/high/critical, never bypassing
  user policy. Routing modes: active_only / active_with_fallback (default) /
  all_devices / specific_device (§21–25, §36–39).
- **Server TTS** behind a `TTSProvider` abstraction: EdgeTTS (default) / Piper /
  Kokoro, with configurable fallback (§28–33).
- **Actions**: button + text_input; first-response-wins across devices;
  correlation_id; idempotency-key; threading; silent notifications (§41–48).
- **Notification vs Delivery** are separate; read state is user-level, display
  is device-level (§49–52).
- **Transport**: WebSocket for desktop + Android foreground; FCM as a wake
  signal only on Android background (§55–56).

## Data stores

- **PostgreSQL** — see §67 for the required tables.
- **Redis** — presence/activity/active/ws/idempotency/pairing keys, all TTL'd
  (§68).
- **Object storage** — MinIO (dev) / S3-compatible (prod); short-lived signed
  URLs, no permanent public URLs (§35, §69).

## Phased plan (§77)

1. **Backend Foundation** — FastAPI, Postgres, Redis, auth, multi-user, device &
   agent registry, docker-compose.
2. **Notification Core** — notification API/DB, routing, activity scoring,
   delivery lifecycle, WebSocket.
3. **Desktop Client** — macOS then Linux: login, pairing, presence, WS, text
   notifications, client TTS, ACK.
4. **Android** — Flutter, FCM, presence, IMU classification, client TTS, Voice
   Alerts Mode.
5. **Server TTS** — provider abstraction (EdgeTTS default).
6. **Agent Audio** — upload, MinIO, audio_id, signed URL, playback.
7. **Actions** — button, text_input, first-response-wins, correlation_id, WS
   events, webhooks (HMAC-signed).
8. **Web Admin** — device/agent/preferences/TTS management, history, users.

## Testing (§78–81)

pytest for auth, multi-user isolation, agent scopes, notification creation,
idempotency, routing, presence scoring, fallback, voice policy,
first-response-wins, expired action, webhook signature; plus integration tests
with fake desktop/phone/agent and the two presence scenarios (§80–81).
