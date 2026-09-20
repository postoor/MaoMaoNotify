"""Application settings, loaded from environment / .env."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database / cache
    database_url: str = "postgresql+asyncpg://maomao:maomao@localhost:5432/maomao"
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 30
    refresh_token_ttl_days: int = 30
    pairing_token_ttl_minutes: int = 5

    # Delivery fallback (§53): escalate to the next device if no ACK in time.
    fallback_timer_enabled: bool = True

    # Object storage. minio_endpoint is how the SERVER reaches MinIO (inside the
    # compose network, e.g. http://minio:9000); minio_public_url is the host that
    # CLIENTS use to download presigned audio URLs (must be reachable by devices,
    # e.g. http://<lan-or-tailscale-ip>:9000). Defaults to minio_endpoint.
    minio_endpoint: str = "http://localhost:9000"
    minio_public_url: str = ""
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "maomao-audio"

    # Push
    fcm_project_id: str = ""

    # TTS (§28–33)
    tts_provider: str = "edge_tts"
    tts_fallback_provider: str = "client_tts"
    edge_tts_voice: str = "zh-TW-HsiaoChenNeural"
    piper_binary_path: str = "piper"
    piper_model_path: str = ""
    kokoro_endpoint: str = "http://localhost:8880"
    kokoro_model: str = "kokoro"
    kokoro_voice: str = "af_sky"
    audio_url_ttl_seconds: int = 3600


settings = Settings()
