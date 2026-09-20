---
name: maomao-notify
description: >-
  Send a push/voice notification to the user (lksdub) on their devices
  (desktop / phone) via their self-hosted MaoMaoNotify server. Use to ping the
  user when a long-running task finishes, a build/deploy/test completes or
  fails, something needs their attention or input, or whenever the user asks to
  be notified / "ping me" / "叫我" / "跑完通知我". Sends text or spoken (TTS)
  alerts with a priority.
---

# MaoMaoNotify — notify the user from an agent

MaoMaoNotify is the user's self-hosted notification platform. As an agent you
POST to its Agent API and the server routes the alert to whichever device the
user is currently on (desktop / Android). Use the bundled `notify.py` (it sits
next to this file) — it needs no dependencies, just Python 3.

## When to use

- A long task you were running has **finished** (build, deploy, migration, data
  job, test suite) — ping so the user can come back.
- Something **failed** or **needs the user** (a decision, a credential, review).
- The user explicitly asked to be notified / "ping me when done" / "跑完叫我".

Don't notify for trivial or every-step progress — one message at a meaningful
moment. Keep the text short and specific ("部署完成", not "the operation you
requested has now completed successfully").

## Setup

`notify.py` reads two environment variables:

- `MAOMAO_URL` — the server base URL (e.g. `http://100.106.153.5:8287`).
- `MAOMAO_TOKEN` — an **agent token** with the `notification:send` scope
  (add `presence:read` to use `--presence`).

Get the token from the Web Admin (`/admin` → **Agents** → new agent → copy the
token, shown once) or the API. The token must belong to the account whose
devices the user actually uses. If the vars are unset, the helper says so — tell
the user to set them rather than guessing.

## Usage

Run the bundled helper (it lives in this skill's folder as `notify.py`; use its
full path if you are not in that folder):

```bash
python3 notify.py "部署完成 ✔"
python3 notify.py --priority high --title "CI" "測試失敗：3 個 case 紅了"
python3 notify.py --voice server_tts --lang zh-TW "NAS 備份完成"
tail -n1 build.log | python3 notify.py --priority low
python3 notify.py --idempotency-key deploy-42 "部署完成"   # retries won't double-ping
python3 notify.py --presence                               # which device is active
```

Flags: `--title`, `--priority {low,normal,high,critical}` (default normal),
`--voice {client_tts,server_tts}` + `--lang`,
`--routing {active_only,active_with_fallback,all_devices}`, `--correlation-id`,
`--idempotency-key`, `--presence`.

On success it prints `sent: <id> (<status>)`. A non-2xx prints the server's error
message — surface it (e.g. `insufficient_scope` = token lacks `notification:send`;
401 / `invalid_credentials` = bad or expired token; connection refused = wrong
`MAOMAO_URL` or the server is down).

## Interactive notifications (buttons / text reply)

The API also supports actions (buttons, text input) with first-response-wins and
HMAC-signed webhook callbacks (`notification.responded`). `notify.py` does not
send those or wait for a reply, because receiving the answer needs a webhook
endpoint the agent can be reached at. If the user wants a prompt-and-wait flow,
say it needs a webhook receiver and point at `POST /api/v1/notifications` (with an
`actions` array) + `POST /api/v1/agents/{id}/webhooks`.

## Notes

- One notification per meaningful moment; use `--idempotency-key` when a step may
  retry so the user isn't pinged twice.
- `--voice` is only spoken if the target device has TTS / Voice Alerts enabled;
  otherwise it shows as a normal notification.
- The server decides routing/presentation under the user's own policies — the
  agent only requests; it never targets a specific device by default.
- Not a Claude Code agent? `notify.py` is a plain CLI, or just
  `POST {MAOMAO_URL}/api/v1/notifications` with `Authorization: Bearer <token>`
  and `{"title","message","type":"text","priority"}`. See `INSTALL.md`.
