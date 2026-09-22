import 'package:maomao_client/android/native_bridge.dart';
import 'package:maomao_client/audio/audio_player.dart';
import 'package:maomao_client/tts/speaker.dart';

/// A fake CommandRunner returning canned output per executable.
class FakeRunner {
  FakeRunner(this.responses);
  final Map<String, String?> responses;
  final List<String> calls = [];

  Future<String?> call(String exe, List<String> args) async {
    calls.add(exe);
    return responses.containsKey(exe) ? responses[exe] : null;
  }
}

/// Records calls instead of hitting the platform channel.
class FakeBridge implements NativeBridge {
  final List<String> calls = [];
  bool speakResult = true;
  bool notifyResult = true;

  @override
  Future<bool> speak(String text, {String? language}) async {
    calls.add('speak:$text');
    return speakResult;
  }

  @override
  Future<bool> showNotification(String title, String body, {String priority = 'normal'}) async {
    calls.add('notify:$title:$priority');
    return notifyResult;
  }

  @override
  Future<bool> playAudio(String url) async {
    calls.add('play:$url');
    return true;
  }

  @override
  Future<void> startVoiceAlerts() async => calls.add('start');

  @override
  Future<void> stopVoiceAlerts() async => calls.add('stop');
}

/// Records the URLs it was asked to play; [result] controls success.
class FakeAudioPlayer implements AudioPlayer {
  FakeAudioPlayer({this.result = true});
  bool result;
  final List<String> played = [];

  @override
  Future<bool> play(String url) async {
    played.add(url);
    return result;
  }
}

/// Records spoken text; [result] controls success.
class FakeSpeaker implements Speaker {
  FakeSpeaker({this.result = true});
  bool result;
  final List<String> spoken = [];

  @override
  Future<bool> speak(String text, {String? language}) async {
    spoken.add(text);
    return result;
  }
}
