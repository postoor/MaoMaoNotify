import 'package:flutter_test/flutter_test.dart';
import 'package:maomao_client/app_state.dart';
import 'package:maomao_client/main.dart';
import 'package:maomao_client/settings/settings_store.dart';
import 'package:maomao_client/voice_alerts/voice_alerts_controller.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'fakes.dart';

void main() {
  testWidgets('shows setup screen when unconfigured', (tester) async {
    SharedPreferences.setMockInitialValues({});
    final settings = await SettingsStore.load();
    final state = AppState(settings: settings);
    final voiceAlerts = VoiceAlertsController(bridge: FakeBridge());

    await tester.pumpWidget(MaoMaoApp(state, voiceAlerts));
    await tester.pump();

    expect(find.text('MaoMaoNotify — Setup'), findsOneWidget);
    expect(find.text('Log in'), findsOneWidget);
  });
}
