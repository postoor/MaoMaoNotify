"""Application settings, loaded from environment / .env."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # Database / cache
    database_url: str = Field(
        "postgresql+asyncpg://maomao:maomao@localhost:5432/maomao",
        validation_alias="DATABASE_URL",
    )
    redis_url: str = Field("redis://localhost:6379/0", validation_alias="REDIS_URL")

    # Auth
    jwt_secret: str = Field("change-me", validation_alias="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", validation_alias="JWT_ALGORITHM")
    access_token_ttl_minutes: int = Field(30, validation_alias="ACCESS_TOKEN_TTL_MINUTES")
    refresh_token_ttl_days: int = Field(30, validation_alias="REFRESH_TOKEN_TTL_DAYS")
    pairing_token_ttl_minutes: int = Field(5, validation_alias="PAIRING_TOKEN_TTL_MINUTES")

    # Delivery fallback (§53): escalate to the next device if no ACK in time.
    fallback_timer_enabled: bool = Field(True, validation_alias="FALLBACK_TIMER_ENABLED")

    # Object storage. minio_endpoint is how the SERVER reaches MinIO (inside the
    # compose network, e.g. http://minio:9000); minio_public_url is the host that
    # CLIENTS use to download presigned audio URLs (must be reachable by devices,
    # e.g. http://<lan-or-tailscale-ip>:9000). Defaults to minio_endpoint.
    minio_endpoint: str = Field("http://localhost:9000", validation_alias="MINIO_ENDPOINT")
    minio_public_url: str = Field("", validation_alias="MINIO_PUBLIC_URL")
    minio_access_key: str = Field("minioadmin", validation_alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field("minioadmin", validation_alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field("maomao-audio", validation_alias="MINIO_BUCKET")

    # Push
    fcm_project_id: str = Field("", validation_alias="FCM_PROJECT_ID")

    # TTS (§28–33)
    tts_provider: str = Field("edge_tts", validation_alias="TTS_PROVIDER")
    tts_fallback_provider: str = Field("client_tts", validation_alias="TTS_FALLBACK_PROVIDER")
    edge_tts_voice: str = Field("zh-TW-HsiaoChenNeural", validation_alias="EDGE_TTS_VOICE")
    piper_binary_path: str = Field("piper", validation_alias="PIPER_BINARY_PATH")
    piper_model_path: str = Field("", validation_alias="PIPER_MODEL_PATH")
    kokoro_endpoint: str = Field("http://localhost:8880", validation_alias="KOKORO_ENDPOINT")
    kokoro_model: str = Field("kokoro", validation_alias="KOKORO_MODEL")
    kokoro_voice: str = Field("af_sky", validation_alias="KOKORO_VOICE")
    audio_url_ttl_seconds: int = Field(3600, validation_alias="AUDIO_URL_TTL_SECONDS")

    # Web admin static files. Empty means the repository's web/ directory.
    web_admin_dir: str = Field("", validation_alias="WEB_ADMIN_DIR")


settings = Settings()
