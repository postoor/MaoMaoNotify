import 'package:flutter/foundation.dart';

import '../android/native_bridge.dart';

/// Voice Alerts Mode (§57). Must be explicitly enabled by the user; when on,
/// Android runs a foreground media service for reliable background audio. The
/// UI must clearly show whether it is enabled.
class VoiceAlertsController extends ChangeNotifier {
  VoiceAlertsController({
    NativeBridge? bridge,
    this.onPersist,
    bool initialEnabled = false,
  })  : _bridge = bridge ?? MethodChannelBridge(),
        _enabled = initialEnabled;

  final NativeBridge _bridge;
  final Future<void> Function(bool)? onPersist;
  bool _enabled;

  bool get enabled => _enabled;

  Future<void> setEnabled(bool value) async {
    if (value == _enabled) return;
    _enabled = value;
    if (value) {
      await _bridge.startVoiceAlerts();
    } else {
      await _bridge.stopVoiceAlerts();
    }
    await onPersist?.call(value);
    notifyListeners();
  }

  Future<void> toggle() => setEnabled(!_enabled);
}
