import 'dart:async';

import 'package:unifiedpush/unifiedpush.dart';

import 'push_service.dart';

/// UnifiedPush-backed push (§56 alt) — self-hosted, no Firebase. A distributor
/// app on the device (e.g. self-hosted ntfy) holds the connection; when it
/// delivers a message we emit a wake signal and the app fetches from the server.
/// The endpoint URL is reported via [endpoints] so it can be registered server-
/// side (POST /devices/push-endpoint).
class UnifiedPushService implements PushService {
  static const instanceName = "maomao";

  final _wake = StreamController<void>.broadcast();
  final _endpoints = StreamController<String>.broadcast();
  String? _endpoint;

  /// New/updated UnifiedPush endpoint URLs.
  Stream<String> get endpoints => _endpoints.stream;

  @override
  Stream<void> get wakeSignals => _wake.stream;

  Future<void> init() async {
    await UnifiedPush.initialize(
      onNewEndpoint: (PushEndpoint endpoint, String instance) {
        _endpoint = endpoint.url;
        _endpoints.add(endpoint.url);
      },
      onMessage: (PushMessage message, String instance) {
        // Content is a wake hint; the app fetches unread from the server (§56).
        _wake.add(null);
      },
      onUnregistered: (String instance) {
        _endpoint = null;
      },
    );
  }

  @override
  Future<String?> register() async {
    await UnifiedPush.tryUseCurrentOrDefaultDistributor();
    await UnifiedPush.register(instance: instanceName);
    return _endpoint;
  }

  @override
  Future<void> dispose() async {
    await _wake.close();
    await _endpoints.close();
  }
}
