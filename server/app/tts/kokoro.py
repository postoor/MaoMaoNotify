"""Kokoro local TTS provider (§32). Talks to an OpenAI-compatible
`/v1/audio/speech` endpoint (e.g. kokoro-fastapi)."""

import httpx

from app.tts.base import AudioResult, TTSProvider, TTSProviderError


class KokoroProvider(TTSProvider):
    name = "kokoro"

    def __init__(
        self,
        endpoint: str = "http://localhost:8880",
        model: str = "kokoro",
        default_voice: str = "af_sky",
        timeout: float = 30.0,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.default_voice = default_voice
        self.timeout = timeout

    async def synthesize(
        self,
        text: str,
        language: str | None = None,
        voice: str | None = None,
        options: dict | None = None,
    ) -> AudioResult:
        if not text.strip():
            raise TTSProviderError(self.name, "empty text")
        selected = voice or self.default_voice
        payload = {
            "model": self.model,
            "input": text,
            "voice": selected,
            "response_format": "mp3",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.endpoint}/v1/audio/speech", json=payload)
        except httpx.HTTPError as exc:
            raise TTSProviderError(self.name, str(exc)) from exc
        if resp.status_code != 200 or not resp.content:
            raise TTSProviderError(self.name, f"HTTP {resp.status_code}")
        content_type = resp.headers.get("content-type", "audio/mpeg").split(";")[0]
        return AudioResult(resp.content, content_type, selected, language, self.name)
