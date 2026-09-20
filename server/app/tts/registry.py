"""TTS provider selection (§29, §33). Default provider is config-driven."""

from app.core.config import Settings
from app.tts.base import TTSProvider
from app.tts.edge import EdgeTTSProvider
from app.tts.kokoro import KokoroProvider
from app.tts.piper import PiperProvider

_ALIASES = {
    "default": "edge_tts",
    "edge": "edge_tts",
    "edge_tts": "edge_tts",
    "piper": "piper",
    "kokoro": "kokoro",
}


def resolve_provider_name(requested: str | None, settings: Settings) -> str:
    """Map a requested provider (or 'default'/None) to a concrete provider name."""
    if requested is None or requested == "default":
        requested = settings.tts_provider
    return _ALIASES.get(requested, requested)


def build_provider(requested: str | None, settings: Settings) -> TTSProvider:
    name = resolve_provider_name(requested, settings)
    if name == "edge_tts":
        return EdgeTTSProvider(default_voice=settings.edge_tts_voice)
    if name == "piper":
        return PiperProvider(settings.piper_binary_path, settings.piper_model_path)
    if name == "kokoro":
        return KokoroProvider(
            settings.kokoro_endpoint, settings.kokoro_model, settings.kokoro_voice
        )
    raise ValueError(f"unknown TTS provider: {requested}")
