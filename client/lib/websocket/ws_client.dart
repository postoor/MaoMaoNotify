import 'dart:async';
import 'dart:convert';

import 'package:web_socket_channel/web_socket_channel.dart';

import '../models/app_notification.dart';
import 'ws_messages.dart';

/// WebSocket transport (§55): receives notification deliveries and sends
/// ACK / read / ping. Thin wrapper around [WebSocketChannel]; message shapes
/// come from [ws_messages].
class WsClient {
  WsClient({required this.baseUrl, required this.deviceToken});

  final String baseUrl;
  final String deviceToken;

  WebSocketChannel? _channel;
  bool _closed = false;
  int _retry = 0;
  final _notifications = StreamController<AppNotification>.broadcast();
  final _resolved = StreamController<String>.broadcast();

  Stream<AppNotification> get notifications => _notifications.stream;

  /// Notification IDs resolved elsewhere (§44) — the UI should disable buttons.
  Stream<String> get resolved => _resolved.stream;
  bool get isConnected => _channel != null;

  void connect() {
    _closed = false;
    _open();
  }

  void _open() {
    final channel = WebSocketChannel.connect(wsUrl(baseUrl, deviceToken));
    _channel = channel;
    channel.stream.listen(
      _onMessage,
      onDone: _scheduleReconnect,
      onError: (_) => _scheduleReconnect(),
      cancelOnError: true,
    );
  }

  void _onMessage(dynamic data) {
    _retry = 0; // healthy connection — reset backoff
    final decoded = jsonDecode(data as String);
    if (decoded is! Map) return;
    final event = parseServerEvent(decoded.cast<String, dynamic>());
    if (event is NotificationEvent) {
      _notifications.add(event.notification);
    } else if (event is ActionResolvedEvent) {
      _resolved.add(event.notificationId);
    }
  }

  /// Reconnect with capped exponential backoff after a drop (server restart,
  /// network blip) so the client keeps receiving without an app restart.
  void _scheduleReconnect() {
    _channel = null;
    if (_closed) return;
    final seconds = (1 << _retry).clamp(1, 30);
    if (_retry < 5) _retry++;
    Future.delayed(Duration(seconds: seconds), () {
      if (!_closed) _open();
    });
  }

  void _send(Map<String, dynamic> msg) => _channel?.sink.add(jsonEncode(msg));

  void ack(String notificationId, {String status = 'delivered'}) =>
      _send(ackMessage(notificationId, status));

  void markRead(String notificationId) => _send(readMessage(notificationId));

  void respond(String notificationId, String actionId, {String? value}) =>
      _send(responseMessage(notificationId, actionId, value: value));

  void ping() => _send(pingMessage());

  Future<void> close() async {
    _closed = true;
    await _channel?.sink.close();
    _channel = null;
    await _notifications.close();
    await _resolved.close();
  }
}
