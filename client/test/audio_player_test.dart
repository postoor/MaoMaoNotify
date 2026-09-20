import 'package:flutter_test/flutter_test.dart';
import 'package:maomao_client/audio/audio_player.dart';

import 'fakes.dart';

void main() {
  group('DesktopAudioPlayer', () {
    test('fetches then plays via the first available player', () async {
      final runner = FakeRunner({'mpv': ''}); // mpv succeeds
      final player = DesktopAudioPlayer(
        runner: runner.call,
        fetcher: (url) async => [1, 2, 3],
      );
      expect(await player.play('http://x/a.mp3'), isTrue);
      expect(runner.calls.first, 'mpv');
    });

    test('falls through to ffplay when mpv missing', () async {
      final runner = FakeRunner({'mpv': null, 'ffplay': ''});
      final player = DesktopAudioPlayer(
        runner: runner.call,
        fetcher: (url) async => [1, 2, 3],
      );
      expect(await player.play('http://x/a.mp3'), isTrue);
      expect(runner.calls, contains('ffplay'));
    });

    test('returns false when download fails', () async {
      final runner = FakeRunner({'mpv': ''});
      final player = DesktopAudioPlayer(runner: runner.call, fetcher: (url) async => null);
      expect(await player.play('http://x/a.mp3'), isFalse);
      expect(runner.calls, isEmpty);
    });
  });

  test('AndroidAudioPlayer delegates to the bridge', () async {
    final bridge = FakeBridge();
    expect(await AndroidAudioPlayer(bridge).play('http://x/a.mp3'), isTrue);
    expect(bridge.calls, contains('play:http://x/a.mp3'));
  });
}
