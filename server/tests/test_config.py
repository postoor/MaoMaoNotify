"""Application settings loaded from process environment and dotenv files."""

from app.core.config import Settings


def test_settings_load_explicit_environment_names(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=sqlite+aiosqlite:///dotenv.db\n"
        "MINIO_PUBLIC_URL=http://dotenv.example:9000\n"
        "ACCESS_TOKEN_TTL_MINUTES=17\n"
        "FALLBACK_TIMER_ENABLED=false\n",
        encoding="utf-8",
    )
    for name in (
        "DATABASE_URL",
        "MINIO_PUBLIC_URL",
        "ACCESS_TOKEN_TTL_MINUTES",
        "FALLBACK_TIMER_ENABLED",
    ):
        monkeypatch.delenv(name, raising=False)

    loaded = Settings(_env_file=env_file)

    assert loaded.database_url == "sqlite+aiosqlite:///dotenv.db"
    assert loaded.minio_public_url == "http://dotenv.example:9000"
    assert loaded.access_token_ttl_minutes == 17
    assert loaded.fallback_timer_enabled is False


def test_process_environment_overrides_dotenv(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("TTS_PROVIDER=piper\n", encoding="utf-8")
    monkeypatch.setenv("TTS_PROVIDER", "kokoro")

    loaded = Settings(_env_file=env_file)

    assert loaded.tts_provider == "kokoro"
