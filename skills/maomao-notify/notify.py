#!/usr/bin/env python3
"""Send a notification to the user via their self-hosted MaoMaoNotify server.

Zero dependencies (stdlib only). Reads config from the environment:
    MAOMAO_URL    base server URL, e.g. http://100.106.153.5:8287
    MAOMAO_TOKEN  an agent token with the notification:send scope
                  (+ presence:read for --presence)

Examples:
    notify.py "部署完成"
    notify.py --title "CI" --priority high "測試失敗：3 個 case 紅了"
    notify.py --voice server_tts --lang zh-TW "NAS 備份完成"
    echo "build done" | notify.py --priority low
    notify.py --presence            # print which device is active
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

PRIORITIES = ("low", "normal", "high", "critical")
ROUTES = ("active_only", "active_with_fallback", "all_devices")


def _req(method, url, token, body=None, extra_headers=None):
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    if extra_headers:
        headers.update(extra_headers)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"error": {"message": raw or e.reason}}
    except urllib.error.URLError as e:
        print(f"maomao-notify: cannot reach {url}: {e.reason}", file=sys.stderr)
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser(prog="notify.py", description="Send a MaoMaoNotify notification.")
    ap.add_argument("message", nargs="?", help="message text (or pipe via stdin)")
    ap.add_argument("--title", default="Claude Code")
    ap.add_argument("--priority", default="normal", choices=PRIORITIES)
    ap.add_argument("--voice", choices=("client_tts", "server_tts"),
                    help="speak it aloud instead of a text notification")
    ap.add_argument("--lang", default="zh-TW", help="voice language (default zh-TW)")
    ap.add_argument("--routing", choices=ROUTES, help="delivery routing mode")
    ap.add_argument("--correlation-id", help="opaque id echoed back in responses/webhooks")
    ap.add_argument("--idempotency-key", help="dedupe key — same key won't create a 2nd notification")
    ap.add_argument("--presence", action="store_true",
                    help="print the user's active device instead of sending")
    args = ap.parse_args()

    url = os.environ.get("MAOMAO_URL")
    token = os.environ.get("MAOMAO_TOKEN")
    if not url or not token:
        print("maomao-notify: set MAOMAO_URL and MAOMAO_TOKEN in the environment.", file=sys.stderr)
        sys.exit(2)
    base = url.rstrip("/") + "/api/v1"

    if args.presence:
        status, data = _req("GET", f"{base}/agent/presence", token)
        if status == 200:
            print(json.dumps(data, ensure_ascii=False, indent=2))
            return
        print(f"maomao-notify: presence failed ({status}): {_msg(data)}", file=sys.stderr)
        sys.exit(1)

    message = args.message
    if message is None and not sys.stdin.isatty():
        message = sys.stdin.read().strip()
    if not message:
        print("maomao-notify: no message given.", file=sys.stderr)
        sys.exit(2)

    body = {"title": args.title, "priority": args.priority}
    if args.voice:
        body["type"] = "voice"
        body["voice"] = {"source": args.voice, "language": args.lang}
        body["content"] = {"text": message}
    else:
        body["type"] = "text"
        body["message"] = message
    if args.routing:
        body["routing"] = {"mode": args.routing}
    if args.correlation_id:
        body["correlation_id"] = args.correlation_id

    headers = {}
    if args.idempotency_key:
        headers["Idempotency-Key"] = args.idempotency_key

    status, data = _req("POST", f"{base}/notifications", token, body, headers)
    if status == 201:
        print(f"sent: {data.get('id')} ({data.get('status')})")
        return
    print(f"maomao-notify: send failed ({status}): {_msg(data)}", file=sys.stderr)
    sys.exit(1)


def _msg(data):
    if isinstance(data, dict) and isinstance(data.get("error"), dict):
        return data["error"].get("message", "unknown error")
    return str(data)


if __name__ == "__main__":
    main()
