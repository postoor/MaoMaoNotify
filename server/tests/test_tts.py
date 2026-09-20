"""TTS provider registry + Edge voice selection (§28–33)."""

import pytest

from app.core.config import settings
from app.tts.edge import EdgeTTSProvider
from app.tts.kokoro import KokoroProvider
from app.tts.piper import PiperProvider
from app.tts.registry import build_provider, resolve_provider_name


def test_resolve_provider_name():
    assert resolve_provider_name(None, settings) == "edge_tts"
    assert resolve_provider_name("default", settings) == "edge_tts"
    assert resolve_provider_name("edge", settings) == "edge_tts"
    assert resolve_provider_name("kokoro", settings) == "kokoro"


def test_build_provider_types():
    assert isinstance(build_provider("edge_tts", settings), EdgeTTSProvider)
    assert isinstance(build_provider("piper", settings), PiperProvider)
    assert isinstance(build_provider("kokoro", settings), KokoroProvider)


def test_build_unknown_raises():
    with pytest.raises(ValueError, match="unknown TTS provider"):
        build_provider("bogus", settings)


def test_edge_voice_selection():
    p = EdgeTTSProvider(default_voice="DEFAULT")
    assert p.voice_for("zh-TW", None) == "zh-TW-HsiaoChenNeural"
    assert p.voice_for("en-US", None) == "en-US-AriaNeural"
    assert p.voice_for(None, "custom-voice") == "custom-voice"  # explicit wins
    assert p.voice_for("xx-YY", None) == "DEFAULT"  # unknown → default
