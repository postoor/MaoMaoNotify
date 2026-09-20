"""In-process WebSocket connection registry (§55).

Single-instance authoritative map of device_id -> WebSocket. The Redis
``ws:device:{device}`` key (§68) mirrors online state for future multi-instance
fan-out.
"""

from redis.asyncio import Redis
from starlette.websockets import WebSocket

from app.core import redis_keys


class ConnectionManager:
    def __init__(self) -> None:
        self._conns: dict[str, WebSocket] = {}

    async def connect(self, device_id: str, ws: WebSocket, redis: Redis | None = None) -> None:
        await ws.accept()
        self._conns[device_id] = ws
        if redis is not None:
            await redis.set(redis_keys.ws_device(device_id), "1", ex=redis_keys.ACTIVE_TTL)

    async def disconnect(self, device_id: str, redis: Redis | None = None) -> None:
        self._conns.pop(device_id, None)
        if redis is not None:
            await redis.delete(redis_keys.ws_device(device_id))

    def is_online(self, device_id: str) -> bool:
        return device_id in self._conns

    async def send(self, device_id: str, message: dict) -> bool:
        ws = self._conns.get(device_id)
        if ws is None:
            return False
        await ws.send_json(message)
        return True


manager = ConnectionManager()
