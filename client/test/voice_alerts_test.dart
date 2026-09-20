import 'package:flutter_test/flutter_test.dart';
import 'package:maomao_client/voice_alerts/voice_alerts_controller.dart';

import 'fakes.dart';

void main() {
  test('enabling starts the foreground service and persists', () async {
    final bridge = FakeBridge();
    var persisted = <bool>[];
    final c = VoiceAlertsController(bridge: bridge, onPersist: (v) async => persisted.add(v));

    await c.setEnabled(true);
    expect(c.enabled, isTrue);
    expect(bridge.calls, contains('start'));
    expect(persisted, [true]);
  });

  test('disabling stops the service', () async {
    final bridge = FakeBridge();
    final c = VoiceAlertsController(bridge: bridge, initialEnabled: true);
    await c.setEnabled(false);
    expect(c.enabled, isFalse);
    expect(bridge.calls, contains('stop'));
  });

  test('setEnabled is idempotent', () async {
    final bridge = FakeBridge();
    final c = VoiceAlertsController(bridge: bridge);
    await c.setEnabled(true);
    await c.setEnabled(true);
    expect(bridge.calls.where((x) => x == 'start').length, 1);
  });

  test('toggle flips state', () async {
    final bridge = FakeBridge();
    final c = VoiceAlertsController(bridge: bridge);
    await c.toggle();
    expect(c.enabled, isTrue);
    await c.toggle();
    expect(c.enabled, isFalse);
  });
}
