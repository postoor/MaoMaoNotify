import '../android/native_bridge.dart';
import 'client_tts.dart';

/// Platform-agnostic client TTS (§26, §60).
abstract class Speaker {
  Future<bool> speak(String text, {String? language});
}

/// Desktop: shell-based system TTS (spd-say / say).
class DesktopSpeaker implements Speaker {
  DesktopSpeaker([ClientTts? tts]) : _tts = tts ?? ClientTts();
  final ClientTts _tts;

  @override
  Future<bool> speak(String text, {String? language}) =>
      _tts.speak(text, language: language);
}

/// Android: native TextToSpeech via the platform channel.
class AndroidSpeaker implements Speaker {
  AndroidSpeaker([NativeBridge? bridge]) : _bridge = bridge ?? MethodChannelBridge();
  final NativeBridge _bridge;

  @override
  Future<bool> speak(String text, {String? language}) =>
      _bridge.speak(text, language: language);
}
