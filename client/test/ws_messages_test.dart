import 'package:flutter_test/flutter_test.dart';
import 'package:maomao_client/websocket/ws_messages.dart';

void main() {
  test('message builders', () {
    expect(ackMessage('msg_1', 'delivered'),
        {'type': 'ack', 'notification_id': 'msg_1', 'status': 'delivered'});
    expect(readMessage('msg_1'), {'type': 'read', 'notification_id': 'msg_1'});
    expect(pingMessage(), {'type': 'ping'});
  });

  test('parseServerEvent → notification', () {
    final ev = parseServerEvent({
      'event': 'notification',
      'notification': {'id': 'msg_1', 'type': 'text', 'title': 't'},
    });
    expect(ev, isA<NotificationEvent>());
    expect((ev as NotificationEvent).notification.id, 'msg_1');
  });

  test('parseServerEvent → pong and unknown', () {
    expect(parseServerEvent({'event': 'pong'}), isA<PongEvent>());
    expect(parseServerEvent({'event': 'nope'}), isA<UnknownEvent>());
  });

  test('responseMessage builder', () {
    expect(responseMessage('msg_1', 'retry'),
        {'type': 'response', 'notification_id': 'msg_1', 'action_id': 'retry'});
    expect(responseMessage('msg_1', 'version', value: 'v1'),
        {'type': 'response', 'notification_id': 'msg_1', 'action_id': 'version', 'value': 'v1'});
  });

  test('parseServerEvent → action_resolved', () {
    final ev = parseServerEvent(
      {'event': 'action_resolved', 'notification_id': 'msg_1', 'action_id': 'retry'},
    );
    expect(ev, isA<ActionResolvedEvent>());
    expect((ev as ActionResolvedEvent).notificationId, 'msg_1');
    expect(ev.actionId, 'retry');
  });

  test('wsUrl derives ws/wss endpoint with token', () {
    expect(wsUrl('http://localhost:8000', 'tok').toString(),
        'ws://localhost:8000/api/v1/ws?token=tok');
    expect(wsUrl('https://host', 'tok').scheme, 'wss');
    expect(wsUrl('http://host:8000/', 'tok').path, '/api/v1/ws');
  });
}
