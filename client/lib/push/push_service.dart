import '../api/api_client.dart';
import '../models/app_notification.dart';

/// Push transport abstraction (§56). On Android, FCM is a *wake signal only* —
/// the real payload is fetched from the server. Wiring FCM requires a Firebase
/// project (google-services.json) and the firebase_messaging plugin; that is
/// left as an integration point. The default is a no-op so the app runs (and
/// builds) without Firebase configured.
abstract class PushService {
  /// Register for push and return the transport token (null if unavailable).
  Future<String?> register();

  /// Fires when a background wake signal arrives; listeners should fetch
  /// pending notifications from the server.
  Stream<void> get wakeSignals;

  Future<void> dispose();
}

class NoopPushService implements PushService {
  @override
  Future<String?> register() async => null;

  @override
  Stream<void> get wakeSignals => const Stream.empty();

  @override
  Future<void> dispose() async {}
}

/// On a wake signal, fetch the notifications the client hasn't seen yet (§56):
/// unread notifications from the server, newest first.
Future<List<AppNotification>> fetchPending(ApiClient api, String accessToken) async {
  final all = await api.listNotifications(accessToken);
  return all.where((n) => !n.isRead).toList();
}
