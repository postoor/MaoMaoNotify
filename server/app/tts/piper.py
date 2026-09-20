"""Piper local TTS provider (§31). Runs the piper binary over a voice model."""

import asyncio

from app.tts.base import AudioResult, TTSProvider, TTSProviderError


class PiperProvider(TTSProvider):
    name = "piper"

    def __init__(self, binary_path: str = "piper", model_path: str = ""):
        self.binary_path = binary_path
        self.model_path = model_path

    async def synthesize(
        self,
        text: str,
        language: str | None = None,
        voice: str | None = None,
        options: dict | None = None,
    ) -> AudioResult:
        if not text.strip():
            raise TTSProviderError(self.name, "empty text")
        model = voice or self.model_path
        if not model:
            raise TTSProviderError(self.name, "no model configured")
        try:
            proc = await asyncio.create_subprocess_exec(
                self.binary_path, "--model", model, "--output_file", "-",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate(input=text.encode())
        except FileNotFoundError as exc:
            raise TTSProviderError(self.name, f"binary not found: {self.binary_path}") from exc
        if proc.returncode != 0 or not stdout:
            raise TTSProviderError(self.name, stderr.decode(errors="replace")[:200] or "no audio")
        return AudioResult(stdout, "audio/wav", model, language, self.name)
