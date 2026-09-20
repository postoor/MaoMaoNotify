import 'package:flutter/services.dart';

/// Bridge to Android-native capabilities (§26 client TTS, text notification,
/// §57 Voice Alerts foreground service). Abstract so it can be faked in tests.
abstract class NativeBridge {
  Future<bool> speak(String text, {String? language});
  Future<bool> showNotification(String title, String body, {String priority = 'normal'});
  Future<bool> playAudio(String url);
  Future<void> startVoiceAlerts();
  Future<void> stopVoiceAlerts();
}

/// Real implementation over the `maomao/android` MethodChannel handled by
/// MainActivity.kt. Missing-plugin errors (e.g. on non-Android) degrade to
/// a safe no-op.
class MethodChannelBridge implements NativeBridge {
  static const _ch = MethodChannel('maomao/android');

  @override
  Future<bool> speak(String text, {String? language}) async {
    try {
      return await _ch.invokeMethod<bool>('speak', {
            'text': text,
            'language': language,
          }) ??
          false;
    } on PlatformException {
      return false;
    } on MissingPluginException {
      return false;
    }
  }

  @override
  Future<bool> showNotification(String title, String body, {String priority = 'normal'}) async {
    try {
      return await _ch.invokeMethod<bool>('showNotification', {
            'title': title,
            'body': body,
            'priority': priority,
          }) ??
          false;
    } on PlatformException {
      return false;
    } on MissingPluginException {
      return false;
    }
  }

  @override
  Future<bool> playAudio(String url) async {
    try {
      return await _ch.invokeMethod<bool>('playAudio', {'url': url}) ?? false;
    } on PlatformException {
      return false;
    } on MissingPluginException {
      return false;
    }
  }

  @override
  Future<void> startVoiceAlerts() async {
    try {
      await _ch.invokeMethod<void>('startVoiceAlerts');
    } on PlatformException {
      // ignore
    } on MissingPluginException {
      // ignore
    }
  }

  @override
  Future<void> stopVoiceAlerts() async {
    try {
      await _ch.invokeMethod<void>('stopVoiceAlerts');
    } on PlatformException {
      // ignore
    } on MissingPluginException {
      // ignore
    }
  }
}
