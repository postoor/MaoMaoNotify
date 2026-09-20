# MaoMaoNotify Web Admin

Vanilla HTML/JS single-page admin (no build step), served by the API server at
**`/admin`** (mounted from this directory). Talks to the same-origin REST API
at `/api/v1`, storing the JWT in `localStorage` with automatic refresh.

Tabs (§70): Devices (list, pairing, rename, delete), Agents (create + token,
webhooks), Preferences (manual presence, Quiet Hours), Voice Settings (per-device
voice policy), Notifications (history), Server TTS (admin — default provider),
User Management (admin).

## Run

```bash
docker compose up            # → http://localhost:8000/admin/
# or locally: uv run uvicorn app.main:app --reload → http://localhost:8000/admin/
```

Log in with a user created via `app.manage create-user` (make it `--role admin`
to see the admin tabs).
