import 'dart:io';

import '../models/app_notification.dart';
import '../system/command_runner.dart';
import 'notifier.dart';

/// Shows desktop notifications: Linux via `notify-send` (libnotify), macOS via
/// `osascript`. Silent-presentation notifications are recorded but not popped
/// (§48).
class DesktopNotifier implements Notifier {
  DesktopNotifier({CommandRunner runner = defaultCommandRunner}) : _run = runner;

  final CommandRunner _run;

  static const _urgency = {
    'low': 'low',
    'normal': 'normal',
    'high': 'critical',
    'critical': 'critical',
  };

  /// Returns true if a popup was shown (false when silent or on failure).
  @override
  Future<bool> show(AppNotification n) async {
    if (n.isSilent) return false;
    final title = n.title ?? 'MaoMaoNotify';
    final message = n.message ?? '';

    if (Platform.isMacOS) {
      String esc(String s) => s.replaceAll('\\', r'\\').replaceAll('"', r'\"');
      final out = await _run('osascript', [
        '-e',
        'display notification "${esc(message)}" with title "${esc(title)}"',
      ]);
      return out != null;
    }

    final urgency = _urgency[n.priority] ?? 'normal';
    final out = await _run('notify-send', [
      '-u', urgency,
      '-a', 'MaoMaoNotify',
      title,
      message,
    ]);
    return out != null;
  }
}
