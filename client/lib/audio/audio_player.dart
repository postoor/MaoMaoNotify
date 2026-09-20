import 'dart:io';

import 'package:http/http.dart' as http;

import '../android/native_bridge.dart';
import '../system/command_runner.dart';

/// Plays a notification's audio asset (server-TTS output or agent-uploaded
/// audio) downloaded from its signed URL (§34, §36).
abstract class AudioPlayer {
  Future<bool> play(String url);
}

/// Fetches the audio bytes for a URL (injectable for tests).
typedef AudioFetcher = Future<List<int>?> Function(String url);

Future<List<int>?> _httpFetch(String url) async {
  try {
    final resp = await http.get(Uri.parse(url));
    if (resp.statusCode != 200) return null;
    return resp.bodyBytes;
  } on http.ClientException {
    return null;
  }
}

/// Desktop: download to a temp file and play via the first available system
/// player (mpv / ffplay / mpg123 / paplay).
class DesktopAudioPlayer implements AudioPlayer {
  DesktopAudioPlayer({CommandRunner runner = defaultCommandRunner, AudioFetcher? fetcher})
      : _run = runner,
        _fetch = fetcher ?? _httpFetch;

  final CommandRunner _run;
  final AudioFetcher _fetch;

  static const _players = <String, List<String>>{
    'mpv': ['--no-video', '--really-quiet'],
    'ffplay': ['-nodisp', '-autoexit', '-loglevel', 'quiet'],
    'mpg123': ['-q'],
    'paplay': [],
  };

  @override
  Future<bool> play(String url) async {
    final bytes = await _fetch(url);
    if (bytes == null || bytes.isEmpty) return false;
    final file = File(
      '${Directory.systemTemp.path}/maomao_${DateTime.now().microsecondsSinceEpoch}.audio',
    );
    await file.writeAsBytes(bytes);
    try {
      for (final entry in _players.entries) {
        final out = await _run(entry.key, [...entry.value, file.path]);
        if (out != null) return true;
      }
      return false;
    } finally {
      if (file.existsSync()) {
        try {
          await file.delete();
        } on FileSystemException {
          // ignore
        }
      }
    }
  }
}

/// Android: native MediaPlayer via the platform channel.
class AndroidAudioPlayer implements AudioPlayer {
  AndroidAudioPlayer([NativeBridge? bridge]) : _bridge = bridge ?? MethodChannelBridge();
  final NativeBridge _bridge;

  @override
  Future<bool> play(String url) => _bridge.playAudio(url);
}
