"""In-memory storage for tests."""

from app.storage.base import StorageService


class InMemoryStorage(StorageService):
    def __init__(self) -> None:
        self._objects: dict[str, tuple[bytes, str]] = {}

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        self._objects[key] = (data, content_type)

    async def signed_url(self, key: str, ttl_seconds: int) -> str:
        return f"memory://{key}?ttl={ttl_seconds}"

    async def presigned_put_url(self, key: str, content_type: str, ttl_seconds: int) -> str:
        return f"memory://put/{key}?ttl={ttl_seconds}"

    async def stat(self, key: str) -> int | None:
        obj = self._objects.get(key)
        return len(obj[0]) if obj else None

    async def get(self, key: str) -> bytes:
        return self._objects[key][0]
