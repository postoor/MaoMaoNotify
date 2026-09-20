import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:maomao_client/api/api_client.dart';
import 'package:maomao_client/api/api_exception.dart';
import 'package:maomao_client/models/observation.dart';

http.Response _json(Object body, int status) =>
    http.Response(jsonEncode(body), status, headers: {'content-type': 'application/json'});

void main() {
  test('setBaseUrl retargets requests and strips trailing slash', () async {
    String origin = '';
    final mock = MockClient((req) async {
      origin = req.url.origin;
      return _json({'access_token': 'a', 'refresh_token': 'r'}, 200);
    });
    final api = ApiClient(baseUrl: 'http://localhost:8000', client: mock);
    api.setBaseUrl('http://100.106.153.5:8287/');
    expect(api.baseUrl, 'http://100.106.153.5:8287');
    await api.login('you@example.com', 'pw');
    expect(origin, 'http://100.106.153.5:8287');
  });

  test('login parses token pair', () async {
    final mock = MockClient((req) async {
      expect(req.url.path, '/api/v1/auth/login');
      expect(jsonDecode(req.body)['email'], 'e@x.com');
      return _json({'access_token': 'a', 'refresh_token': 'r', 'token_type': 'bearer'}, 200);
    });
    final api = ApiClient(baseUrl: 'http://x', client: mock);
    final pair = await api.login('e@x.com', 'pw');
    expect(pair.accessToken, 'a');
  });

  test('error envelope becomes ApiException', () async {
    final mock = MockClient((req) async => _json(
          {'error': {'code': 'invalid_credentials', 'message': 'bad', 'request_id': 'req_1'}},
          401,
        ));
    final api = ApiClient(baseUrl: 'http://x', client: mock);
    expect(
      () => api.login('e@x.com', 'pw'),
      throwsA(isA<ApiException>()
          .having((e) => e.code, 'code', 'invalid_credentials')
          .having((e) => e.isAuthError, 'isAuthError', true)),
    );
  });

  test('redeemPairing returns device id + token', () async {
    final mock = MockClient((req) async {
      expect(req.url.path, '/api/v1/devices/pairing/redeem');
      return _json({'device_id': 'dev_1', 'device_token': 'dtok'}, 200);
    });
    final api = ApiClient(baseUrl: 'http://x', client: mock);
    final res = await api.redeemPairing(code: '12345678', platform: 'linux');
    expect(res.deviceId, 'dev_1');
    expect(res.deviceToken, 'dtok');
  });

  test('listNotifications maps to models', () async {
    final mock = MockClient((req) async => _json([
          {'id': 'msg_1', 'type': 'text', 'title': 't', 'message': 'm', 'status': 'sent',
           'priority': 'normal', 'expires_at': '2030-01-01T00:00:00Z',
           'created_at': '2026-01-01T00:00:00Z'},
        ], 200));
    final api = ApiClient(baseUrl: 'http://x', client: mock);
    final list = await api.listNotifications('access');
    expect(list.single.id, 'msg_1');
  });

  test('reportPresence sends bearer + observation body', () async {
    var authHeader = '';
    final mock = MockClient((req) async {
      authHeader = req.headers['authorization'] ?? '';
      expect(jsonDecode(req.body)['screen'], 'on');
      return _json({'status': 'ok'}, 200);
    });
    final api = ApiClient(baseUrl: 'http://x', client: mock);
    await api.reportPresence('devtok', const Observation(screen: 'on', locked: false));
    expect(authHeader, 'Bearer devtok');
  });

  test('registerPushEndpoint posts the endpoint with device auth', () async {
    var body = '';
    var auth = '';
    final mock = MockClient((req) async {
      expect(req.url.path, '/api/v1/devices/push-endpoint');
      body = req.body;
      auth = req.headers['authorization'] ?? '';
      return _json({'status': 'ok'}, 200);
    });
    final api = ApiClient(baseUrl: 'http://x', client: mock);
    await api.registerPushEndpoint('devtok', 'http://ntfy/upXYZ');
    expect(auth, 'Bearer devtok');
    expect(jsonDecode(body)['endpoint'], 'http://ntfy/upXYZ');
  });
}
