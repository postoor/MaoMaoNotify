import 'package:flutter_test/flutter_test.dart';
import 'package:maomao_client/models/app_notification.dart';
import 'package:maomao_client/notification/desktop_notifier.dart';
import 'package:maomao_client/presence/observer.dart';
import 'package:maomao_client/tts/client_tts.dart';

import 'fakes.dart';

void main() {
  group('presence parsing', () {
    test('parseIdleMs', () {
      expect(parseIdleMs('12345'), 12345);
      expect(parseIdleMs(null), isNull);
      expect(parseIdleMs('abc'), isNull);
    });

    test('parseLockedHint', () {
      expect(parseLockedHint('LockedHint=yes'), isTrue);
      expect(parseLockedHint('LockedHint=no'), isFalse);
      expect(parseLockedHint(null), isNull);
    });

    test('LinuxPresenceObserver uses xprintidle + loginctl', () async {
      final runner = FakeRunner({'xprintidle': '5000', 'loginctl': 'LockedHint=no'});
      final obs = await LinuxPresenceObserver(runner: runner.call, sessionId: '1')
          .observe(appState: 'foreground');
      expect(obs.lastInteractionMs, 5000);
      expect(obs.locked, isFalse);
      expect(obs.screen, 'on');
      expect(obs.appState, 'foreground');
    });
  });

  group('client TTS', () {
    test('uses spd-say when available', () async {
      final runner = FakeRunner({'spd-say': ''});
      final ok = await ClientTts(runner: runner.call).speak('hello');
      expect(ok, isTrue);
      expect(runner.calls.first, 'spd-say');
    });

    test('falls back to espeak-ng', () async {
      final runner = FakeRunner({'spd-say': null, 'espeak-ng': ''});
      final ok = await ClientTts(runner: runner.call).speak('hi');
      expect(ok, isTrue);
      expect(runner.calls, contains('espeak-ng'));
    });

    test('empty text does nothing', () async {
      final runner = FakeRunner({'spd-say': ''});
      expect(await ClientTts(runner: runner.call).speak('   '), isFalse);
      expect(runner.calls, isEmpty);
    });
  });

  group('desktop notifier', () {
    AppNotification n({String presentation = 'normal', String priority = 'normal'}) =>
        AppNotification(id: 'm', type: 'text', title: 't', message: 'm',
            priority: priority, presentation: presentation);

    test('shows normal notification', () async {
      final runner = FakeRunner({'notify-send': ''});
      expect(await DesktopNotifier(runner: runner.call).show(n()), isTrue);
      expect(runner.calls, contains('notify-send'));
    });

    test('skips silent notification', () async {
      final runner = FakeRunner({'notify-send': ''});
      expect(await DesktopNotifier(runner: runner.call).show(n(presentation: 'silent')), isFalse);
      expect(runner.calls, isEmpty);
    });
  });
}
