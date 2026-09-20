"""Agent webhook delivery with HMAC signatures (§66).

Signature scheme (verifiable by the receiver):
    signature = HMAC_SHA256(secret, f"{timestamp}.".encode() + body)
sent as header ``X-MaoMao-Signature: sha256=<hex>`` alongside ``X-MaoMao-Timestamp``
and ``X-MaoMao-Event-Id`` (timestamp + event_id let receivers reject replays).
"""

import hashlib
import hmac
import json
import time

import httpx

from app.core.ids import new_id
from app.core.logging import get_logger
from app.models.agent import AgentWebhook

log = get_logger("webhooks")


def sign(secret: str, timestamp: str, body: bytes) -> str:
    mac = hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256)
    return mac.hexdigest()


def verify(secret: str, timestamp: str, body: bytes, signature: str) -> bool:
    expected = f"sha256={sign(secret, timestamp, body)}"
    return hmac.compare_digest(expected, signature)


async def send_event(
    webhooks: list[AgentWebhook],
    event: str,
    payload: dict,
    *,
    transport: httpx.BaseTransport | None = None,
) -> None:
    """Best-effort POST to each webhook. Never raises (won't fail the request)."""
    if not webhooks:
        return
    event_id = new_id("evt")
    timestamp = str(int(time.time()))
    body = json.dumps(
        {"event": event, "event_id": event_id, "timestamp": timestamp, **payload},
        ensure_ascii=False,
    ).encode()

    async with httpx.AsyncClient(transport=transport, timeout=5.0) as client:
        for wh in webhooks:
            headers = {
                "Content-Type": "application/json",
                "X-MaoMao-Event": event,
                "X-MaoMao-Event-Id": event_id,
                "X-MaoMao-Timestamp": timestamp,
                "X-MaoMao-Signature": f"sha256={sign(wh.secret, timestamp, body)}",
            }
            try:
                await client.post(wh.url, content=body, headers=headers)
            except httpx.HTTPError:
                log.warning("webhook delivery failed", extra={"event": event})
