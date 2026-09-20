"""TTS provider abstraction (§28)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

_EXT = {
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/ogg": "ogg",
    "audio/opus": "opus",
    "audio/aac": "aac",
    "audio/mp4": "m4a",
}


def extension_for(content_type: str) -> str:
    return _EXT.get(content_type.split(";")[0].strip().lower(), "bin")


class TTSProviderError(Exception):
    """Raised when a provider fails to synthesize (§30 tts_provider_error)."""

    def __init__(self, provider: str, message: str):
        self.provider = provider
        super().__init__(f"{provider}: {message}")


@dataclass
class AudioResult:
    audio: bytes
    content_type: str  # e.g. audio/mpeg, audio/wav
    voice: str | None
    language: str | None
    provider: str

    @property
    def extension(self) -> str:
        return {
            "audio/mpeg": "mp3",
            "audio/wav": "wav",
            "audio/x-wav": "wav",
            "audio/ogg": "ogg",
        }.get(self.content_type, "bin")


class TTSProvider(ABC):
    name: str

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        language: str | None = None,
        voice: str | None = None,
        options: dict | None = None,
    ) -> AudioResult:
        ...
