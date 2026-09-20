import 'dart:io';

import '../system/command_runner.dart';

/// Client-side system TTS (§26, §60). On Linux, prefers `spd-say`
/// (speech-dispatcher), falling back to `espeak-ng` / `espeak`. If the
/// preferred voice/engine is missing, it degrades to whatever is available.
class ClientTts {
  ClientTts({CommandRunner runner = defaultCommandRunner}) : _run = runner;

  final CommandRunner _run;

  /// Returns true if speech was dispatched to some engine.
  Future<bool> speak(String text, {String? language, double rate = 1.0}) async {
    if (text.trim().isEmpty) return false;

    if (Platform.isMacOS) {
      // macOS built-in `say`.
      final r = await _run('say', [text]);
      return r != null;
    }

    // spd-say: -r rate is -100..100; map 0.5..2.0 → -50..50 roughly.
    final spdRate = ((rate - 1.0) * 100).clamp(-100, 100).round().toString();
    final spd = await _run('spd-say', ['-w', '-r', spdRate, text]);
    if (spd != null) return true;

    for (final engine in const ['espeak-ng', 'espeak']) {
      final out = await _run(engine, [text]);
      if (out != null) return true;
    }
    return false;
  }

  static Future<bool> isAvailable({CommandRunner runner = defaultCommandRunner}) async {
    final engines = Platform.isMacOS
        ? const ['say']
        : const ['spd-say', 'espeak-ng', 'espeak'];
    for (final e in engines) {
      if (await _which(e)) return true;
    }
    return false;
  }

  static Future<bool> _which(String exe) async {
    try {
      final r = await Process.run('which', [exe]);
      return r.exitCode == 0;
    } on ProcessException {
      return false;
    }
  }
}
