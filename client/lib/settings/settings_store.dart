import 'package:shared_preferences/shared_preferences.dart';

/// Persistent local settings and credentials (per-viewer, on-device only).
class SettingsStore {
  SettingsStore(this._prefs);

  final SharedPreferences _prefs;

  static Future<SettingsStore> load() async =>
      SettingsStore(await SharedPreferences.getInstance());

  static const _kServerUrl = 'server_url';
  static const _kAccess = 'access_token';
  static const _kRefresh = 'refresh_token';
  static const _kDeviceId = 'device_id';
  static const _kDeviceToken = 'device_token';
  static const _kVoiceAlerts = 'voice_alerts_enabled';

  String get serverUrl => _prefs.getString(_kServerUrl) ?? 'http://localhost:8000';
  Future<void> setServerUrl(String v) => _prefs.setString(_kServerUrl, v);

  String? get accessToken => _prefs.getString(_kAccess);
  String? get refreshToken => _prefs.getString(_kRefresh);

  Future<void> setTokens(String access, String refresh) async {
    await _prefs.setString(_kAccess, access);
    await _prefs.setString(_kRefresh, refresh);
  }

  String? get deviceId => _prefs.getString(_kDeviceId);
  String? get deviceToken => _prefs.getString(_kDeviceToken);

  Future<void> setDevice(String id, String token) async {
    await _prefs.setString(_kDeviceId, id);
    await _prefs.setString(_kDeviceToken, token);
  }

  bool get voiceAlertsEnabled => _prefs.getBool(_kVoiceAlerts) ?? false;
  Future<void> setVoiceAlertsEnabled(bool v) => _prefs.setBool(_kVoiceAlerts, v);

  bool get isLoggedIn => accessToken != null && refreshToken != null;
  bool get isPaired => deviceId != null && deviceToken != null;

  Future<void> clear() async {
    for (final k in [_kAccess, _kRefresh, _kDeviceId, _kDeviceToken]) {
      await _prefs.remove(k);
    }
  }
}
