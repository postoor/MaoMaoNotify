import 'package:flutter_test/flutter_test.dart';
import 'package:maomao_client/models/app_notification.dart';
import 'package:maomao_client/notification/notifier.dart';
import 'package:maomao_client/tts/speaker.dart';

import 'fakes.dart';

AppNotification note({String presentation = 'normal', String priority = 'normal'}) =>
    AppNotification(
      id: 'm', type: 'text', title: 't', message: 'body',
      presentation: presentation, priority: priority,
    );

void main() {
  test('AndroidSpeaker delegates to the bridge', () async {
    final bridge = FakeBridge();
    expect(await AndroidSpeaker(bridge).speak('hi', language: 'zh-TW'), isTrue);
    expect(bridge.calls, contains('speak:hi'));
  });

  test('AndroidNotifier shows normal, skips silent', () async {
    final bridge = FakeBridge();
    final n = AndroidNotifier(bridge);
    expect(await n.show(note(priority: 'high')), isTrue);
    expect(bridge.calls, contains('notify:t:high'));

    bridge.calls.clear();
    expect(await n.show(note(presentation: 'silent')), isFalse);
    expect(bridge.calls, isEmpty);
  });
}
