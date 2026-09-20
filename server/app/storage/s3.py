"""S3-compatible storage (MinIO in dev, §35, §69). boto3 is sync, so calls run
in a thread to avoid blocking the event loop."""

import asyncio

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import Settings
from app.storage.base import StorageService


class S3Storage(StorageService):
    def __init__(self, settings: Settings):
        self.bucket = settings.minio_bucket
        creds = {
            "aws_access_key_id": settings.minio_access_key,
            "aws_secret_access_key": settings.minio_secret_key,
            "region_name": "us-east-1",
            "config": Config(signature_version="s3v4"),
        }
        # Internal client for put/head/get (server → MinIO).
        self._client = boto3.client("s3", endpoint_url=settings.minio_endpoint, **creds)
        # Signer client bound to the CLIENT-reachable host, so presigned URLs
        # resolve for devices (the signature is over that host).
        public = settings.minio_public_url or settings.minio_endpoint
        self._signer = (
            self._client if public == settings.minio_endpoint
            else boto3.client("s3", endpoint_url=public, **creds)
        )
        self._ensured = False

    def _ensure_bucket(self) -> None:
        if self._ensured:
            return
        try:
            self._client.head_bucket(Bucket=self.bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self.bucket)
        self._ensured = True

    def _put(self, key: str, data: bytes, content_type: str) -> None:
        self._ensure_bucket()
        self._client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)

    def _signed_url(self, key: str, ttl: int) -> str:
        self._ensure_bucket()
        return self._signer.generate_presigned_url(
            "get_object", Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=ttl
        )

    def _presigned_put_url(self, key: str, content_type: str, ttl: int) -> str:
        self._ensure_bucket()
        return self._signer.generate_presigned_url(
            "put_object",
            Params={"Bucket": self.bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=ttl,
        )

    def _stat(self, key: str) -> int | None:
        try:
            return self._client.head_object(Bucket=self.bucket, Key=key)["ContentLength"]
        except ClientError:
            return None

    def _get(self, key: str) -> bytes:
        return self._client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        await asyncio.to_thread(self._put, key, data, content_type)

    async def signed_url(self, key: str, ttl_seconds: int) -> str:
        return await asyncio.to_thread(self._signed_url, key, ttl_seconds)

    async def presigned_put_url(self, key: str, content_type: str, ttl_seconds: int) -> str:
        return await asyncio.to_thread(self._presigned_put_url, key, content_type, ttl_seconds)

    async def stat(self, key: str) -> int | None:
        return await asyncio.to_thread(self._stat, key)

    async def get(self, key: str) -> bytes:
        return await asyncio.to_thread(self._get, key)
