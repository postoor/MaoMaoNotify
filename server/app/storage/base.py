"""Object storage abstraction for audio assets (§35)."""

from abc import ABC, abstractmethod


class StorageService(ABC):
    @abstractmethod
    async def put(self, key: str, data: bytes, content_type: str) -> None: ...

    @abstractmethod
    async def signed_url(self, key: str, ttl_seconds: int) -> str:
        """Short-lived signed download URL (§35 — never a permanent public URL)."""

    @abstractmethod
    async def presigned_put_url(self, key: str, content_type: str, ttl_seconds: int) -> str:
        """Short-lived signed upload URL for the agent to PUT audio to (§34)."""

    @abstractmethod
    async def stat(self, key: str) -> int | None:
        """Object size in bytes, or None if it does not exist."""

    @abstractmethod
    async def get(self, key: str) -> bytes: ...
