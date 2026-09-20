import 'package:maomao_client/android/native_bridge.dart';

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
