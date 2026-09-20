import 'dart:io';

/// Runs an external command and returns stdout (trimmed), or null on failure.
/// Injectable so system integrations can be unit-tested without real processes.
typedef CommandRunner = Future<String?> Function(String exe, List<String> args);

Future<String?> defaultCommandRunner(String exe, List<String> args) async {
  try {
    final result = await Process.run(exe, args);
    if (result.exitCode != 0) return null;
    return (result.stdout as String).trim();
  } on ProcessException {
    return null;
  }
}
