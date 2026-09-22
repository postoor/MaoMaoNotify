import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/app_notification.dart';
import '../models/observation.dart';
import '../models/token_pair.dart';
import 'api_exception.dart';

/// Thin REST client for the MaoMaoNotify server. Stateless: callers pass the
/// access/device token per request. Token refresh lives in the session layer.
class ApiClient {
  ApiClient({required String baseUrl, http.Client? client})
      : baseUrl = _normalize(baseUrl),
        _http = client ?? http.Client();

  /// Mutable so the Setup screen can point it at the entered server URL.
  String baseUrl;
  final http.Client _http;

  static String _normalize(String u) => u.trim().replaceAll(RegExp(r'/+$'), '');

  void setBaseUrl(String url) => baseUrl = _normalize(url);

  Uri _uri(String path) => Uri.parse('$baseUrl/api/v1$path');

  Map<String, String> _headers({String? bearer, Map<String, String>? extra}) => {
        'Content-Type': 'application/json',
        if (bearer != null) 'Authorization': 'Bearer $bearer',
        ...?extra,
      };

  dynamic _decode(http.Response resp) {
    final body = resp.body.isEmpty ? null : jsonDecode(resp.body);
    if (resp.statusCode >= 200 && resp.statusCode < 300) return body;
    final err = (body is Map ? body['error'] : null) as Map<String, dynamic>?;
    throw ApiException(
      resp.statusCode,
      (err?['code'] as String?) ?? 'http_error',
      (err?['message'] as String?) ?? 'Request failed',
      requestId: err?['request_id'] as String?,
    );
  }

  // --- auth ---

  Future<TokenPair> login(String email, String password) async {
    final resp = await _http.post(_uri('/auth/login'),
        headers: _headers(), body: jsonEncode({'email': email, 'password': password}));
    return TokenPair.fromJson(_decode(resp) as Map<String, dynamic>);
  }

  Future<TokenPair> refresh(String refreshToken) async {
    final resp = await _http.post(_uri('/auth/refresh'),
        headers: _headers(), body: jsonEncode({'refresh_token': refreshToken}));
    return TokenPair.fromJson(_decode(resp) as Map<String, dynamic>);
  }

  // --- pairing (device side) ---

  Future<({String deviceId, String deviceToken})> redeemPairing({
    String? token,
    String? code,
    required String platform,
    String? architecture,
    String? detectedName,
    List<String> capabilities = const [],
  }) async {
    final resp = await _http.post(
      _uri('/devices/pairing/redeem'),
      headers: _headers(),
      body: jsonEncode({
        if (token != null) 'token': token,
        if (code != null) 'code': code,
        'platform': platform,
        if (architecture != null) 'architecture': architecture,
        if (detectedName != null) 'detected_name': detectedName,
        'capabilities': capabilities,
      }),
    );
    final j = _decode(resp) as Map<String, dynamic>;
    return (deviceId: j['device_id'] as String, deviceToken: j['device_token'] as String);
  }

  // --- presence (device auth) ---

  Future<void> reportPresence(String deviceToken, Observation obs) async {
    final resp = await _http.post(_uri('/presence'),
        headers: _headers(bearer: deviceToken), body: jsonEncode(obs.toJson()));
    _decode(resp);
  }

  /// Register (or clear, with null) this device's UnifiedPush endpoint (§56 alt).
  Future<void> registerPushEndpoint(String deviceToken, String? endpoint) async {
    final resp = await _http.post(_uri('/devices/push-endpoint'),
        headers: _headers(bearer: deviceToken), body: jsonEncode({'endpoint': endpoint}));
    _decode(resp);
  }

  // --- notifications (user auth) ---

  Future<List<AppNotification>> listNotifications(String accessToken) async {
    final resp = await _http.get(_uri('/notifications'), headers: _headers(bearer: accessToken));
    final list = _decode(resp) as List<dynamic>;
    return list.map((e) => AppNotification.fromJson(e as Map<String, dynamic>)).toList();
  }

  /// Mint a fresh short-lived signed download URL for an audio asset (§35).
  /// The URL stored on a notification expires (AUDIO_URL_TTL_SECONDS), so
  /// (re)playing goes through here to get a currently-valid URL.
  Future<String> getAudioUrl(String accessToken, String audioId) async {
    final resp = await _http.get(_uri('/audio/$audioId'), headers: _headers(bearer: accessToken));
    final j = _decode(resp) as Map<String, dynamic>;
    return j['url'] as String;
  }

  Future<void> markRead(String accessToken, String notificationId) async {
    final resp = await _http.post(_uri('/notifications/$notificationId/read'),
        headers: _headers(bearer: accessToken));
    _decode(resp);
  }

  void close() => _http.close();
}
