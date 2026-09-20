import '../android/native_bridge.dart';
import '../models/app_notification.dart';

/// Platform-agnostic notification presentation. Silent-presentation
/// notifications are recorded but not popped (§48).
abstract class Notifier {
  Future<bool> show(AppNotification n);
}

/// Android: native NotificationManager via the platform channel.
class AndroidNotifier implements Notifier {
  AndroidNotifier([NativeBridge? bridge]) : _bridge = bridge ?? MethodChannelBridge();
  final NativeBridge _bridge;

  @override
  Future<bool> show(AppNotification n) {
    if (n.isSilent) return Future.value(false);
    return _bridge.showNotification(
      n.title ?? 'MaoMaoNotify',
      n.message ?? '',
      priority: n.priority,
    );
  }
}
