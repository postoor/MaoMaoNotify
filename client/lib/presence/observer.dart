import '../models/observation.dart';
import '../system/command_runner.dart';

/// Produces presence observations from local system signals (§12).
abstract class PresenceObserver {
  Future<Observation> observe({String appState = 'background'});
}

/// Parse `xprintidle` output (idle milliseconds).
int? parseIdleMs(String? out) {
  if (out == null) return null;
  return int.tryParse(out.trim());
}

/// Parse `loginctl show-session <id> -p LockedHint` output → locked?.
bool? parseLockedHint(String? out) {
  if (out == null) return null;
  final line = out.trim().toLowerCase();
  if (line.contains('lockedhint=yes')) return true;
  if (line.contains('lockedhint=no')) return false;
  return null;
}

/// Linux observer using best-effort userspace signals. Real deployments should
/// prefer systemd-logind / DBus and be Wayland-aware (§59); this uses
/// `xprintidle` and `loginctl` when present and degrades gracefully.
class LinuxPresenceObserver implements PresenceObserver {
  LinuxPresenceObserver({CommandRunner runner = defaultCommandRunner, this.sessionId})
      : _run = runner;

  final CommandRunner _run;
  final String? sessionId;

  @override
  Future<Observation> observe({String appState = 'background'}) async {
    final idle = parseIdleMs(await _run('xprintidle', const []));
    bool? locked;
    if (sessionId != null) {
      locked = parseLockedHint(
        await _run('loginctl', ['show-session', sessionId!, '-p', 'LockedHint']),
      );
    }
    return Observation(
      screen: 'on',
      locked: locked,
      lastInteractionMs: idle,
      appState: appState,
      motion: 'stationary',
      timestamp: DateTime.now().toUtc(),
    );
  }
}
