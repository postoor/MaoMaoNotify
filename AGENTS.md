# MaoMaoNotify

Cross-platform AI-agent notification platform. Monorepo: `server/` (FastAPI,
Python 3.13, uv), `client/` (Flutter: Android/macOS/Linux), `web/` (admin).
Design & phased plan: `docs/architecture.md`.

## Notifying the user from an agent

A project Codex skill wraps the Agent API so agents can ping the user:
`.Codex/skills/maomao-notify/` (SKILL.md + notify.py, zero deps; tracked with
the repo). Reads `MAOMAO_URL` + `MAOMAO_TOKEN` (an agent token with
`notification:send`). Usage:
`python3 .Codex/skills/maomao-notify/notify.py "訊息"` (flags: --title,
--priority, --voice, --lang, --routing, --correlation-id, --idempotency-key,
--presence). The token must belong to the account whose devices you use (create
the agent under that user in /admin → Agents).

## Build / run

```bash
cp .env.example .env                 # fill secrets first
docker compose up -d                 # postgres, redis, minio, server
docker compose --profile tts up      # + piper, kokoro (optional)
```

## Server (uv)

```bash
cd server
uv sync
uv run uvicorn app.main:app --reload # http://localhost:8000  (/health)
uv run pytest
uv run ruff check .
uv run alembic upgrade head          # once models exist
```

## Client (Flutter)

```bash
cd client
flutter pub get
flutter analyze
flutter test                       # headless unit/widget tests
flutter build linux --debug        # compile Linux desktop bundle
flutter run -d linux               # live GUI (needs DISPLAY)
```

Platform runners already generated (linux/macos/android). Client shells out to
`notify-send` (desktop popup) and `spd-say`/`espeak` (client TTS) via an
injectable CommandRunner — no native plugins, so no extra build deps.

## Create a user (bootstrap login)

```bash
cd server
uv run python -m app.manage create-user --email you@example.com --password pw --role admin
```

## Packaging / release builds

Artifacts land in `dist/` (gitignored). Android is signed with a RELEASE keystore
at `client/android/app/maomao-release.jks` (config in `client/android/key.properties`,
both gitignored — BACK THEM UP; losing them means no in-place app updates).

```bash
cd client
flutter build apk --release                 # universal APK (dist/…-0.1.0.apk)
flutter build apk --release --split-per-abi  # per-ABI (arm64 for the S21)
flutter build linux --release                # bundle → build/linux/x64/release/bundle
```
Linux package = tar.gz of the release bundle + install.sh (installs to ~/.local)
+ .desktop + maomao-client.png icon; dist/maomao-client-0.1.0-linux-x64.tar.gz.

Branding: hand-drawn ("潦草手繪") black-cat mascot (from the user's cat photo).
- App icon master: /tmp render from an SVG (cat on paper tile, feDisplacement
  rough filter) → magick to Android mipmap-*/ic_launcher.png (48/72/96/144/192)
  and a 256px Linux icon. Re-render via design/ SVGs if regenerating.
- Web admin (web/) is themed to match: paper dot-grid bg, ink #262421, amber
  #E3A02E/#E9B24A, Kalam+Long Cang handwriting, wobbly border-radius boxes,
  inline cat SVG in login + nav (app.js `cat(px)`). Fonts via Google Fonts
  <link> in web/index.html. app.js class names unchanged (pure reskin).
- Design canvas (sketch mockups): design/*.dc.html (Icon, Setup, Main, Admin)
  + canvas.json, seeded to design/maomao-sketch-ui.html, published as an
  Artifact (contract 0.1.31, self+downloads).

## Status

**All 8 phases complete & verified** (details below). Backend: 82 pytest tests
(SQLite + fakeredis); 6 Alembic migrations round-tripped on real Postgres.
Client: 48 flutter tests, Linux + Android builds; live-verified on real Linux
desktop + a physical Galaxy S21. Web admin: served at /admin, renders.

Phase 1 + Phase 2 done & verified. Phase 1: auth (JWT + rotating refresh),
multi-user isolation, device registry + pairing, agent registry + scopes.
Phase 2: activity scoring (§16), presence + active-device hysteresis (§17/§18),
routing engine (§24), notification create API + idempotency + TTL (§40/§46),
delivery lifecycle + fallback (§49–53), WebSocket gateway (§55), presence APIs
incl. agent view (§64). 53 pytest tests green (SQLite + fakeredis); 2 Alembic
migrations round-tripped on real Postgres; full-stack E2E on real PG + Redis.

Phase 3 (Desktop client, Linux-first) done & LIVE-verified. Flutter app with
api/auth/websocket/presence/tts/notification layers + setup/home UI; TTS +
notifier are platform-aware (Linux notify-send/spd-say, macOS osascript/say).
22 flutter tests green, `flutter analyze` clean, `flutter build linux` compiles.
Live E2E on real desktop (see client/tool/live_smoke.dart): pairing → real
WebSocket → agent notification received over the wire → real notify-send popup
+ spd-say speech → ACKs (delivered/displayed/played) persisted server-side.
macOS: NOT tested — the `mac` host has no Flutter/Xcode (user deferred).

Phase 4 (Android) done & verified at build+test level: IMU motion classifier
(§15, pure + tested), AndroidPresenceObserver, sensors_plus/battery_plus wiring,
platform-aware Speaker/Notifier (Android via `maomao/android` MethodChannel →
native TextToSpeech + NotificationManager), Voice Alerts Mode foreground service
(§57, Kotlin VoiceAlertsService + UI toggle), FCM wake→fetch abstraction (§56).
42 flutter tests green, analyze clean, `flutter build apk --debug` compiles the
native Kotlin + plugins. LIVE-verified on a real Samsung Galaxy S21 (Android 15)
via the `x300` adb host: WS delivery → native NotificationManager popup →
native TextToSpeech (delivery reached `played`), real IMU presence score, and
Voice Alerts Mode foreground service (isForeground=true, type mediaPlayback).
FCM is scaffolded behind PushService but NOT wired to a real Firebase project
(needs google-services.json + firebase_messaging).

Phase 5 (Server TTS) done & LIVE-verified. TTSProvider abstraction (§28) with
EdgeTTSProvider (default), PiperProvider, KokoroProvider; config-driven registry
(§29/§33); VoiceSynthesizer synthesizes server_tts notifications → stores to
S3/MinIO → attaches audio_id + presigned audio_url to notification.voice; falls
back to client_tts on provider failure (§30). audio_assets table + migration;
GET /api/v1/audio/{id} returns a short-lived signed URL (§35). Storage layer:
StorageService abstraction, S3Storage (boto3/MinIO), InMemoryStorage (tests).
62 server tests green; migration round-tripped on Postgres; full live E2E:
agent server_tts notification → real Edge-TTS zh-TW synth → stored in MinIO →
downloaded a valid 28KB MP3 via the presigned URL.

Phase 6 (Agent Audio) done & LIVE-verified. POST /api/v1/audio/uploads (agent,
notification:send) returns a presigned PUT URL + audio_id (§34); agent PUTs bytes
to MinIO; a notification with voice.source=agent_audio + audio_id is resolved by
VoiceSynthesizer.attach_agent_audio (validates ownership, HEADs storage for size,
attaches a signed audio_url); errors are clean 400s (missing/unowned/not-uploaded).
Storage gained presigned_put_url + stat. Client playback: AudioPlayer abstraction
(DesktopAudioPlayer downloads + plays via mpv/ffplay/mpg123/paplay; AndroidAudioPlayer
→ native MediaPlayer via bridge.playAudio); app_state plays any voice notification
carrying audio_url and acks 'played'. 68 server tests + 46 client tests green,
APK + Linux build. Live E2E: agent PUT a real 25KB mp3 → notification → downloaded
via signed URL byte-identical (md5 match) → played with mpv.

Phase 7 (Actions) done & LIVE-verified. Notifications carry button / text_input
actions (validated at create); NotificationResponse table + resolved_* columns on
notifications. First-response-wins (§44): POST /notifications/{id}/responses
(device auth) or WS {type:response}; the winner gets 201, later responders 409
action_already_resolved; the user's other devices receive an action_resolved WS
event to disable buttons. correlation_id flows through. Webhooks (§66): register
via POST /agents/{id}/webhooks (secret shown once); on notification.responded the
agent's webhooks get an HMAC-signed POST (X-MaoMao-Signature sha256 over
timestamp.body, plus event_id + timestamp for replay defence). Client: renders
action buttons + text inputs, sends responses over WS, disables on action_resolved.
75 server tests + 48 client tests green; migration round-tripped on Postgres;
APK + Linux build. Live E2E: first-response-wins (201 then 409) + webhook
delivered to a local sink with a signature that verifies (and tamper rejected).

Phase 8 (Web Admin) done & LIVE-verified — ALL 8 PHASES COMPLETE. New backend:
admin user management (GET/POST/DELETE /api/v1/admin/users, require_admin, can't
delete self), admin server-TTS setting (GET/PATCH /admin/settings/tts) stored in
an app_settings key/value table via core/runtime.py and layered over env
(effective_tts_provider; VoiceSynthesizer honours the runtime default), and
device voice-policy prefs (GET/PATCH /devices/{id}/preferences, §37). Web admin
is a build-free vanilla HTML/JS SPA in web/ served by FastAPI at /admin
(StaticFiles, mounted when web/index.html exists; docker-compose mounts ./web:/web).
Tabs: Devices, Agents (+webhooks), Preferences (quiet hours), Voice Settings,
Notifications, Server TTS (admin), User Management (admin). 82 server tests green,
migration round-tripped on Postgres; live: /admin serves, admin API flow works,
headless-Chromium screenshot confirms the SPA renders.

Post-Phase-8 hardening (done & verified):
- ACK-timeout fallback timer (§53): `delivery.schedule_fallback` fires
  `run_fallback` after the plan timeout with its own DB session; wired into
  create_notification (active_with_fallback + >1 target), gated by
  `FALLBACK_TIMER_ENABLED` (tests disable it via an autouse fixture). 83 tests.
- Production packaging: `docker/Dockerfile.prod` (build from repo root) bakes
  server + pinned deps + the web admin (WEB_ADMIN_DIR=/srv/web) and runs
  `alembic upgrade head` on start; `docker-compose.prod.yml` (port via
  ${SERVER_PORT:-8000}, no source mounts, restart policies). `docs/deployment.md`
  covers config/launch/admin/reverse-proxy/gaps. Verified: image builds, serves
  /health + /admin standalone, and full prod compose auto-migrates + admin
  login + admin API work.
Push without Firebase — UnifiedPush + self-hosted ntfy (chosen over FCM):
- Server: devices.push_endpoint column + POST /api/v1/devices/push-endpoint
  (device auth) to register a UnifiedPush endpoint; delivery.send_push_wakes
  POSTs a wake body to the endpoint for OFFLINE android devices with an endpoint
  (called from dispatch). 85 server tests; migration round-tripped. LIVE-verified
  against a real self-hosted ntfy in Docker: offline-android notification →
  server POSTed wake → ntfy received {"type":"wake","notification_id":...}.
- Client: `unifiedpush` ^6.2.0 plugin + UnifiedPushService (init callbacks →
  onNewEndpoint reports URL, onMessage → wake); app_state.registerPushEndpoint
  (POST to server) + handleWake (fetchPending → notifier.show); wired in main
  for Android. 49 client tests, APK + Linux build.
- NOT verified on-device: the ntfy Android app as distributor → our app
  receiving (needs installing/configuring the ntfy distributor app manually).

Still open (need external resources): retention cleanup job, multi-instance
fallback scheduler, full on-device UnifiedPush reception, client actions on-device.

Next: Phase 4 (Android), Phase 5 (Server TTS), Phase 6 (Agent Audio), or
Phase 7 (Actions).

Deferred (documented, not bugs):
- Phase 2 ACK-timeout fallback timer: `delivery.run_fallback()` is wired and
  unit-tested but not attached to a scheduler; availability-based fallback
  (offline primary → next online) IS automatic.
- Phase 2 WS transport now live-verified via client/tool/live_smoke.dart.
- Phase 3 Flutter GUI screens themselves not driven in a test (logic + live
  networking + notify/TTS are verified); macOS/Android builds pending.

## Lessons
- 2026-09-16: Android — voice not playing over http = cleartext. Dart http/WS
  (dart:io) bypass Android's cleartext policy, but native MediaPlayer does NOT →
  http:// audio blocked on release/targetSdk≥28. Fix: `usesCleartextTraffic="true"`
  in the manifest. Also: system notifications need a runtime POST_NOTIFICATIONS
  grant on Android 13+ (added a request in MainActivity.onCreate) — without it
  NotificationManager.notify is silently dropped. Background (screen off ⇒
  offline, no delivery): the app is frozen when backgrounded; staying online +
  receiving needs the foreground service = **enable Voice Alerts Mode** (§57), or
  UnifiedPush for wake-when-killed. In-memory notification list is lost on kill.
- 2026-09-16: server_tts/agent audio silent on clients = single MINIO endpoint.
  The server reaches MinIO at compose host `minio:9000`, but presigned audio
  URLs embed that host → devices can't resolve it. Fix: MINIO_ENDPOINT (server,
  internal) + MINIO_PUBLIC_URL (client-reachable LAN/Tailscale host); S3Storage
  signs GET/PUT with a second client bound to the public host.
- 2026-09-16: "connected but shows offline" — presence came only from the
  client's POST /presence loop; a WS-connected device with no observation read as
  offline. Fix: gateway calls presence.mark_online on WS connect (baseline score,
  doesn't clobber a real one), refresh_online per message, mark_offline on
  disconnect. Also: WsClient had NO auto-reconnect (dev --reload drops WS → dead
  until app restart) — added capped-backoff reconnect; and pair() now connects +
  starts the presence loop so first-time setup doesn't need a restart.
- 2026-09-15: Client bug — ApiClient.baseUrl was `final`, fixed at AppState
  construction to the default (localhost:8000); typing a Server URL in Setup only
  updated settings, so login still hit localhost:8000 (Connection refused). Fix:
  baseUrl mutable + `ApiClient.setBaseUrl` (normalizes, strips trailing /), and
  `AppState.setServerUrl` updates both settings and the client; Setup calls it.
  (WsClient was fine — built fresh in connect() from settings.serverUrl.)
- 2026-09-15: Dev docker-compose bind-mounts ./server:/app, which SHADOWS an
  image venv at /app/.venv; a host-built server/.venv also has a shebang pointing
  at a host path absent in the container → `exec .../uvicorn: no such file or
  directory`. Fix: build the container venv OUTSIDE /app
  (UV_PROJECT_ENVIRONMENT=/opt/venv, PATH=/opt/venv/bin) + server/.dockerignore
  excluding .venv. Dev command has no alembic step → run
  `docker compose exec server alembic upgrade head` after first up.
- 2026-09-14: Starlette 1.6 includes routers lazily (`_IncludedRouter` /
  `_effective_candidates`) → `app.routes` does NOT list included routes; verify
  routing via `/openapi.json` or a live request, not `app.routes`.
- 2026-09-14: Alembic runs sync → use `psycopg` (v3) driver, not asyncpg;
  env.py rewrites `+asyncpg` → `+psycopg` from DATABASE_URL.
- 2026-09-14: ruff flags FastAPI `Depends()` defaults as B008; ignored in
  pyproject (idiomatic pattern).
- 2026-09-14: This box's graphical session is Wayland (session 4, socket
  wayland-0), NOT X11. For CLI-launched GUI/notify/TTS export XDG_RUNTIME_DIR=
  /run/user/1000, WAYLAND_DISPLAY=wayland-0, DBUS_SESSION_BUS_ADDRESS=
  unix:path=/run/user/1000/bus. `loginctl unlock-session 4` unlocks it.
- 2026-09-14: Port :8000 is taken by another of the user's services (uvicorn,
  /opt/venv) — do NOT kill it; use another port (used 8055) for this project.
- 2026-09-14: Dart `main()` return value is NOT the process exit code — set the
  top-level `exitCode` from dart:io instead.
- 2026-09-14: The `mac` SSH host has no Flutter/Dart/Homebrew and only CLT (no
  full Xcode) → can't build macOS .app there without installing Xcode.
- 2026-09-14: Java 26 on PATH still builds Android APK fine (flutter build apk).
  battery_plus/sensors_plus emit a KGP deprecation WARNING (not an error) under
  current Flutter; watch for a future breaking change.
- 2026-09-14: edge-tts (7.2.8) synthesizes fine from this network (needs
  internet to Microsoft). No local piper binary / kokoro server here → those
  providers are unit-tested, not run live. `localhost:8187` is a faster-whisper
  STT server (OpenAI-compatible /v1/audio/transcriptions), NOT TTS — useful
  later for transcribing voice replies (§43), not for Phase 5.
- 2026-09-15: Push without Firebase = UnifiedPush + self-hosted ntfy. Flutter
  `unifiedpush` ^6.2.0: `UnifiedPush.initialize(onNewEndpoint:(PushEndpoint e,..)
  {e.url}, onMessage:(PushMessage m,..){m.content})`, then
  `tryUseCurrentOrDefaultDistributor()` + `register(instance:...)`. Phone needs a
  distributor app (ntfy) installed. ntfy endpoint = a POST-able topic URL; server
  just HTTP POSTs the wake body. `docker run -p 8090:80 binwiederhier/ntfy serve`.
- 2026-09-15: pydantic EmailStr rejects reserved TLDs (`.test`, `.example` bare,
  `.localhost`) via email-validator deliverability — login with `x@y.test` 422s
  even though create-user (plain str) accepts it. Use real-looking domains
  (example.com is fine) in tests/demos.
- 2026-09-15: Prod image must build from the REPO ROOT (context .) with
  `-f docker/Dockerfile.prod` so it can COPY both server/ and web/. The dev
  compose serves web via a ./web:/web bind mount; the prod image bakes it and
  sets WEB_ADMIN_DIR=/srv/web (main.py honours that env override).
- 2026-09-14: MinIO presigned URLs embed the MINIO_ENDPOINT host (localhost:9000
  in dev) — fine locally, but a real device can't resolve it; prod must set
  MINIO_ENDPOINT to a client-reachable host.
- 2026-09-14: Live Android testing rig — a real phone hangs off the `x300` SSH
  host's adb. To let the phone reach this machine's server: run backend here on
  :8055, then `ssh -R 8055:localhost:8055 x300 'adb reverse tcp:8055 tcp:8055'`
  (chain: phone localhost:8055 → x300 → this box). Skip GUI typing by injecting
  shared_prefs: push an XML with `flutter.`-prefixed keys and
  `adb shell run-as <pkg> cp ... shared_prefs/FlutterSharedPreferences.xml`,
  then force-stop + `am start`. Drive UI via `uiautomator dump` + `input tap`
  (content-desc holds the widget label). Clean up: uninstall app, adb
  reverse --remove-all, kill the ssh -R.
