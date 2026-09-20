import 'package:flutter_test/flutter_test.dart';
import 'package:maomao_client/presence/android_presence.dart';

void main() {
  test('composes motion classification, battery, and interaction', () async {
    final obs = await AndroidPresenceObserver(
      motion: () => 'handheld',
      battery: () async => {'level': 80, 'charging': false},
      lastInteractionMs: () => 3000,
    ).observe(appState: 'foreground');

    expect(obs.motion, 'handheld');
    expect(obs.appState, 'foreground');
    expect(obs.lastInteractionMs, 3000);
    expect(obs.battery['level'], 80);
    expect(obs.screen, 'on');

    final json = obs.toJson();
    expect(json['motion'], 'handheld');
    expect(json['app_state'], 'foreground');
    expect(json['last_interaction_ms'], 3000);
  });

  test('battery provider is optional', () async {
    final obs = await AndroidPresenceObserver(motion: () => 'stationary').observe();
    expect(obs.motion, 'stationary');
    expect(obs.battery, isEmpty);
  });
}
