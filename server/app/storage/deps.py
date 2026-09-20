"""Storage dependency — a lazily-created S3/MinIO singleton."""

from functools import lru_cache

from app.core.config import settings
from app.storage.base import StorageService
from app.storage.s3 import S3Storage


@lru_cache(maxsize=1)
def _storage() -> StorageService:
    return S3Storage(settings)


async def get_storage() -> StorageService:
    return _storage()
