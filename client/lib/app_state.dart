import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';

import 'api/api_client.dart';
import 'api/api_exception.dart';
import 'audio/audio_player.dart';
import 'models/app_notification.dart';
import 'notification/notifier.dart';
import 'presence/observer.dart';
import 'presentation.dart';
import 'push/push_service.dart';
import 'settings/settings_store.dart';
import 'tts/speaker.dart';
import 'websocket/ws_client.dart';

/// Coordinates auth, pairing, presence, WebSocket delivery, and presentation
/// (notification popup + client TTS) across desktop and Android (Phase 3–4).
class AppState extends ChangeNotifier {
  AppState({
    required this.settings,
    ApiClient? api,
    Notifier? notifier,
    Speaker? speaker,
    AudioPlayer? audioPlayer,
    PresenceObserver? observer,
  })  : api = api ?? ApiClient(baseUrl: settings.serverUrl),
        notifier = notifier ?? createNotifier(),
        speaker = speaker ?? createSpeaker(),
        audioPlayer = audioPlayer ?? createAudioPlayer(),
        observer = observer ?? LinuxPresenceObserver();

  final SettingsStore settings;
  final ApiClient api;
  final Notifier notifier;
  final Speaker speaker;
  final AudioPlayer audioPlayer;
  final PresenceObserver observer;

  final List<AppNotification> notifications = [];
  final Set<String> resolvedIds = {};
  String status = 'idle';
  WsClient? _ws;
  Timer? _presenceTimer;
  StreamSubscription<AppNotification>? _sub;
  StreamSubscription<String>? _resolvedSub;

  bool isResolved(String notificationId) => resolvedIds.contains(notificationId);

  bool get isLoggedIn => settings.isLoggedIn;
  bool get isPaired => settings.isPaired;

  static List<String> get _capabilities => [
        'text_notification',
        'audio_playback',
        'client_tts',
        'actions',
        'text_reply',
        'presence',
        if (Platform.isAndroid) ...['imu', 'fcm', 'foreground_audio'],
        if (!Platform.isAndroid) ...['desktop_notification', 'system_idle'],
      ];

  static String get _platform {
    if (Platform.isMacOS) return 'macos';
    if (Platform.isAndroid) return 'android';
    return 'linux';
  }

  Future<T> _withAuth<T>(Future<T> Function(String access) fn) async {
    try {
      return await fn(settings.accessToken!);
    } on ApiException catch (e) {
      if (!e.isAuthError) rethrow;
      final pair = await api.refresh(settings.refreshToken!);
      await settings.setTokens(pair.accessToken, pair.refreshToken);
      return await fn(pair.accessToken);
    }
  }

  /// Persist the server URL and point the API client at it (Setup screen).
  Future<void> setServerUrl(String url) async {
    await settings.setServerUrl(url);
    api.setBaseUrl(url);
  }

  Future<void> login(String email, String password) async {
    final pair = await api.login(email, password);
    await settings.setTokens(pair.accessToken, pair.refreshToken);
    status = 'logged in';
    notifyListeners();
  }

  Future<void> pair(String code) async {
    final res = await api.redeemPairing(
      code: code,
      platform: _platform,
      detectedName: Platform.localHostname,
      capabilities: _capabilities,
    );
    await settings.setDevice(res.deviceId, res.deviceToken);
    status = 'paired';
    notifyListeners();
    // Connect + start reporting immediately, so first-time setup doesn't need
    // an app restart to come online.
    connect();
    startPresenceLoop();
  }

  Future<void> loadNotifications() async {
    final list = await _withAuth(api.listNotifications);
    notifications
      ..clear()
      ..addAll(list);
    notifyListeners();
  }

  void connect() {
    if (!isPaired) return;
    final ws = WsClient(baseUrl: settings.serverUrl, deviceToken: settings.deviceToken!);
    _ws = ws;
    _sub = ws.notifications.listen(_onNotification);
    _resolvedSub = ws.resolved.listen((id) {
      resolvedIds.add(id);
      notifyListeners();
    });
    ws.connect();
    status = 'connected';
    notifyListeners();
  }

  /// Respond to a notification action; resolve locally (§44 first-response-wins).
  void respond(AppNotification n, String actionId, {String? value}) {
    _ws?.respond(n.id, actionId, value: value);
    resolvedIds.add(n.id);
    notifyListeners();
  }

  Future<void> _onNotification(AppNotification n) async {
    if (!notifications.any((x) => x.id == n.id)) {
      notifications.insert(0, n);
    }
    _ws?.ack(n.id, status: 'delivered');

    if (!n.isSilent && await notifier.show(n)) {
      _ws?.ack(n.id, status: 'displayed');
    }
    if (n.isVoice) {
      final url = n.voice['audio_url'] as String?;
      if (url != null && url.isNotEmpty) {
        // server_tts / agent_audio: download + play the audio asset.
        if (await audioPlayer.play(url)) _ws?.ack(n.id, status: 'played');
      } else if (n.voice['source'] == 'client_tts') {
        final spoken =
            await speaker.speak(n.message ?? '', language: n.voice['language'] as String?);
        if (spoken) _ws?.ack(n.id, status: 'played');
      }
    }
    notifyListeners();
  }

  /// Register this device's UnifiedPush endpoint with the server (§56 alt).
  Future<void> registerPushEndpoint(String endpoint) async {
    if (!isPaired) return;
    await api.registerPushEndpoint(settings.deviceToken!, endpoint);
  }

  /// Handle a background push wake: fetch unread notifications and present them.
  Future<void> handleWake() async {
    final pending = await _withAuth((access) => fetchPending(api, access));
    for (final n in pending) {
      if (!notifications.any((x) => x.id == n.id)) {
        notifications.insert(0, n);
      }
      if (!n.isSilent) await notifier.show(n);
    }
    notifyListeners();
  }

  Future<void> reportPresenceOnce({String appState = 'foreground'}) async {
    if (!isPaired) return;
    final obs = await observer.observe(appState: appState);
    await api.reportPresence(settings.deviceToken!, obs);
  }

  void startPresenceLoop({Duration interval = const Duration(seconds: 20)}) {
    _presenceTimer?.cancel();
    _presenceTimer = Timer.periodic(interval, (_) => reportPresenceOnce());
  }

  Future<void> logout() async {
    await disconnect();
    await settings.clear();
    notifications.clear();
    status = 'idle';
    notifyListeners();
  }

  Future<void> disconnect() async {
    _presenceTimer?.cancel();
    await _sub?.cancel();
    await _resolvedSub?.cancel();
    await _ws?.close();
    _ws = null;
  }

  @override
  void dispose() {
    disconnect();
    api.close();
    super.dispose();
  }
}
