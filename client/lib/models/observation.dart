/// A presence observation (§12). The client reports observations only — it
/// never declares "I am active". Privacy: no keystrokes, coordinates, URLs, or
/// raw sensor streams (§13).
class Observation {
  const Observation({
    this.screen,
    this.locked,
    this.lastInteractionMs,
    this.appState,
    this.motion,
    this.audio = const {},
    this.battery = const {},
    this.timestamp,
  });

  final String? screen; // "on" | "off"
  final bool? locked;
  final int? lastInteractionMs;
  final String? appState; // "foreground" | "background"
  final String? motion; // stationary | moving | handheld | walking | unknown
  final Map<String, dynamic> audio;
  final Map<String, dynamic> battery;
  final DateTime? timestamp;

  Map<String, dynamic> toJson() => {
        if (screen != null) 'screen': screen,
        if (locked != null) 'locked': locked,
        if (lastInteractionMs != null) 'last_interaction_ms': lastInteractionMs,
        if (appState != null) 'app_state': appState,
        if (motion != null) 'motion': motion,
        'audio': audio,
        'battery': battery,
        if (timestamp != null) 'timestamp': timestamp!.toUtc().toIso8601String(),
      };
}
