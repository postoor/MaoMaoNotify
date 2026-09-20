# Deployment

Two stacks are provided:

- **`docker-compose.yml`** — development: source is bind-mounted, `uvicorn --reload`,
  the web admin is served from `./web`. Fast iteration.
- **`docker-compose.prod.yml`** — production: the server image (`docker/Dockerfile.prod`)
  bakes the server code, pinned dependencies (`uv.lock`, no dev deps), and the web
  admin; it runs DB migrations on start and serves without reload.

## 1. Configure

```bash
cp .env.example .env
```

Set real values (never commit `.env`):

- `JWT_SECRET` — a long random string (`openssl rand -hex 32`).
- `POSTGRES_USER/PASSWORD/DB` and a matching `DATABASE_URL`
  (`postgresql+asyncpg://<user>:<pass>@postgres:5432/<db>`).
- `MINIO_ACCESS_KEY/SECRET_KEY`, and **`MINIO_ENDPOINT` must be a hostname the
  clients can reach** — presigned audio URLs embed it. Behind a reverse proxy,
  set it to the public MinIO/S3 URL (e.g. `https://media.example.com`), not
  `localhost`.
- `TTS_PROVIDER` (default `edge_tts`), `TTS_FALLBACK_PROVIDER` (default `client_tts`).
- Background Android push uses **UnifiedPush + self-hosted ntfy** (no Firebase);
  see "Android background push" below.

## 2. Launch

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

The server container runs `alembic upgrade head` before starting, so the schema
is created/updated automatically.

## 3. Create the first admin

```bash
docker compose -f docker-compose.prod.yml exec server \
  python -m app.manage create-user --email you@example.com --password '<pw>' --role admin
```

Then open **`http://<host>:8000/admin/`** and log in.

## 4. Reverse proxy (recommended)

Put TLS in front (Caddy/nginx/Traefik) and route:

- `/` and `/api` and `/admin` → server `:8000` (WebSocket at `/api/v1/ws` needs
  `Upgrade`/`Connection` headers proxied).
- A public route → MinIO `:9000` matching `MINIO_ENDPOINT` so signed audio URLs
  resolve for clients.

Keep the MinIO console (`:9001`) and Postgres/Redis ports private.

## 5. Clients

- Desktop (Linux/macOS): `flutter build linux` / `flutter build macos`; point the
  app's Server URL at the public API.
- Android: `flutter build apk --release`; background push uses UnifiedPush (below).

## Android background push (UnifiedPush, no Firebase)

The app is built on FCM-free push via [UnifiedPush](https://unifiedpush.org):

1. **Self-host a distributor.** Run ntfy: `docker run -d -p 80:80 binwiederhier/ntfy serve`
   (put it behind TLS; it can be the same box). Any UnifiedPush distributor works.
2. **On the phone**, install the **ntfy** app (F-Droid/Play) and point it at your
   ntfy server — it acts as the UnifiedPush distributor.
3. The MaoMao app registers with the distributor, gets an endpoint URL, and sends
   it to the server (`POST /api/v1/devices/push-endpoint`, device-authenticated).
4. When a notification targets an **offline** Android device that has an endpoint,
   the server POSTs a wake to that endpoint; the app wakes and fetches the
   unread notifications from the server and shows them.

Foreground / connected devices are delivered over WebSocket as usual; the push
path is only the background wake.

## Retention / operations

- Retention defaults (§52): notification metadata 90d, delivery events 30d,
  audio assets 7d, presence Redis-TTL only. (A cleanup job is not yet scheduled —
  see Gaps.)
- Backups: `postgres-data` and `minio-data` volumes.

## Known gaps (not yet wired)

- **On-device UnifiedPush reception**: server→ntfy wake is verified; the full
  phone path (ntfy distributor app → MaoMao app receives → fetch) needs the ntfy
  app installed/configured on the device and hasn't been end-to-end tested here.
- **Retention cleanup job (§52)**: add a scheduled task to prune old
  notifications/deliveries/audio per the retention settings.
- **ACK-timeout fallback** is enabled by default (`FALLBACK_TIMER_ENABLED`); it
  uses in-process timers, so it is single-instance. For multi-instance, move it
  to a shared scheduler/queue.
