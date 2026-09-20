import '../models/app_notification.dart';

/// Pure builders/parsers for WebSocket messages (§55). Kept transport-free so
/// they can be unit-tested without a live socket.

Map<String, dynamic> ackMessage(String notificationId, String status) =>
    {'type': 'ack', 'notification_id': notificationId, 'status': status};

Map<String, dynamic> readMessage(String notificationId) =>
    {'type': 'read', 'notification_id': notificationId};

Map<String, dynamic> responseMessage(String notificationId, String actionId, {String? value}) =>
    {
      'type': 'response',
      'notification_id': notificationId,
      'action_id': actionId,
      if (value != null) 'value': value,
    };

Map<String, dynamic> pingMessage() => {'type': 'ping'};

/// A decoded inbound server event.
sealed class ServerEvent {
  const ServerEvent();
}

class NotificationEvent extends ServerEvent {
  const NotificationEvent(this.notification);
  final AppNotification notification;
}

class PongEvent extends ServerEvent {
  const PongEvent();
}

/// Another device resolved this notification's action (§44) → disable buttons.
class ActionResolvedEvent extends ServerEvent {
  const ActionResolvedEvent(this.notificationId, this.actionId);
  final String notificationId;
  final String? actionId;
}

class UnknownEvent extends ServerEvent {
  const UnknownEvent(this.raw);
  final Map<String, dynamic> raw;
}

ServerEvent parseServerEvent(Map<String, dynamic> msg) {
  switch (msg['event']) {
    case 'notification':
      return NotificationEvent(
        AppNotification.fromJson((msg['notification'] as Map).cast<String, dynamic>()),
      );
    case 'pong':
      return const PongEvent();
    case 'action_resolved':
      return ActionResolvedEvent(
        msg['notification_id'] as String,
        msg['action_id'] as String?,
      );
    default:
      return UnknownEvent(msg);
  }
}

/// Convert an http(s) base URL into the ws(s) endpoint URL with the token.
Uri wsUrl(String baseUrl, String deviceToken) {
  final base = Uri.parse(baseUrl);
  final scheme = base.scheme == 'https' ? 'wss' : 'ws';
  return base.replace(
    scheme: scheme,
    path: '${base.path}/api/v1/ws'.replaceAll('//api', '/api'),
    queryParameters: {'token': deviceToken},
  );
}
