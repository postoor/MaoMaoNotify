import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:maomao_client/api/api_client.dart';
import 'package:maomao_client/push/push_service.dart';

void main() {
  test('NoopPushService is inert', () async {
    final p = NoopPushService();
    expect(await p.register(), isNull);
    expect(await p.wakeSignals.isEmpty, isTrue);
  });

  test('fetchPending returns only unread notifications (§56)', () async {
    final mock = MockClient((req) async => http.Response(
          jsonEncode([
            {'id': 'msg_read', 'type': 'text', 'status': 'sent', 'priority': 'normal',
             'expires_at': '2030-01-01T00:00:00Z', 'created_at': '2026-01-01T00:00:00Z',
             'read_at': '2026-01-01T01:00:00Z'},
            {'id': 'msg_unread', 'type': 'text', 'status': 'sent', 'priority': 'normal',
             'expires_at': '2030-01-01T00:00:00Z', 'created_at': '2026-01-01T00:00:00Z',
             'read_at': null},
          ]),
          200,
          headers: {'content-type': 'application/json'},
        ));
    final api = ApiClient(baseUrl: 'http://x', client: mock);
    final pending = await fetchPending(api, 'access');
    expect(pending.map((n) => n.id), ['msg_unread']);
  });
}
