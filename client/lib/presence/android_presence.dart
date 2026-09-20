import '../models/observation.dart';
import 'observer.dart';

/// Android presence observer (§12, §14, §15). Emits the motion *classification*
/// only, plus screen/lock/battery/interaction — never a raw sensor stream (§13).
/// Providers are injected so this is unit-testable without plugins.
class AndroidPresenceObserver implements PresenceObserver {
  AndroidPresenceObserver({
    required this.motion,
    this.battery,
    this.lastInteractionMs,
    this.screen = 'on',
    this.locked,
  });

  final String Function() motion;
  final Future<Map<String, dynamic>> Function()? battery;
  final int? Function()? lastInteractionMs;
  final String screen;
  final bool? locked;

  @override
  Future<Observation> observe({String appState = 'background'}) async {
    return Observation(
      screen: screen,
      locked: locked,
      lastInteractionMs: lastInteractionMs?.call(),
      appState: appState,
      motion: motion(),
      battery: battery != null ? await battery!() : const {},
      timestamp: DateTime.now().toUtc(),
    );
  }
}
