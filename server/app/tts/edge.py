"""Edge TTS provider (§30) — the default. Uses Microsoft Edge's online voices."""

import edge_tts

from app.tts.base import AudioResult, TTSProvider, TTSProviderError

# Minimal language → default voice map; explicit voice always wins.
_LANG_VOICE = {
    "zh-tw": "zh-TW-HsiaoChenNeural",
    "zh-cn": "zh-CN-XiaoxiaoNeural",
    "zh": "zh-TW-HsiaoChenNeural",
    "en": "en-US-AriaNeural",
    "en-us": "en-US-AriaNeural",
    "ja": "ja-JP-NanamiNeural",
}


class EdgeTTSProvider(TTSProvider):
    name = "edge_tts"

    def __init__(self, default_voice: str = "zh-TW-HsiaoChenNeural"):
        self.default_voice = default_voice

    def voice_for(self, language: str | None, voice: str | None) -> str:
        if voice:
            return voice
        if language:
            mapped = _LANG_VOICE.get(language.lower())
            if mapped:
                return mapped
        return self.default_voice

    async def synthesize(
        self,
        text: str,
        language: str | None = None,
        voice: str | None = None,
        options: dict | None = None,
    ) -> AudioResult:
        if not text.strip():
            raise TTSProviderError(self.name, "empty text")
        opts = options or {}
        kwargs = {}
        for k in ("rate", "volume", "pitch"):
            if isinstance(opts.get(k), str):
                kwargs[k] = opts[k]
        selected = self.voice_for(language, voice)
        try:
            communicate = edge_tts.Communicate(text, selected, **kwargs)
            buf = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    buf += chunk["data"]
        except Exception as exc:
            raise TTSProviderError(self.name, str(exc)) from exc
        if not buf:
            raise TTSProviderError(self.name, "no audio produced")
        return AudioResult(bytes(buf), "audio/mpeg", selected, language, self.name)
