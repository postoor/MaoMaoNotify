/// A notification as seen by the client, parsed from either the WebSocket
/// delivery payload or the REST NotificationOut.
class AppNotification {
  const AppNotification({
    required this.id,
    required this.type,
    this.title,
    this.message,
    this.priority = 'normal',
    this.presentation = 'normal',
    this.voice = const {},
    this.playback = const {},
    this.actions = const [],
    this.correlationId,
    this.threadId,
    this.groupKey,
    this.expiresAt,
    this.readAt,
    this.createdAt,
  });

  final String id;
  final String type; // text | voice
  final String? title;
  final String? message;
  final String priority;
  final String presentation; // normal | silent
  final Map<String, dynamic> voice;
  final Map<String, dynamic> playback;
  final List<dynamic> actions;
  final String? correlationId;
  final String? threadId;
  final String? groupKey;
  final DateTime? expiresAt;
  final DateTime? readAt;

  /// When the server created the notification (§62). Used to show the user when
  /// a notification was received. May be absent on WS payloads from an older
  /// server; the REST list always carries it.
  final DateTime? createdAt;

  bool get isVoice => type == 'voice';
  bool get isSilent => presentation == 'silent';
  bool get isRead => readAt != null;

  /// The stored server-TTS / agent audio asset id, if any. Preferred over
  /// [audioUrl] for playback because it lets the client mint a fresh signed URL
  /// (the stored [audioUrl] is short-lived and may have expired — §35).
  String? get audioId => voice['audio_id'] as String?;

  /// The (possibly expired) signed download URL captured at create time.
  String? get audioUrl => voice['audio_url'] as String?;

  bool get isClientTts => voice['source'] == 'client_tts';

  /// True when this notification has voice the client can play (a downloadable
  /// audio asset or client-side TTS).
  bool get hasPlayableVoice =>
      isVoice &&
      ((audioId?.isNotEmpty ?? false) ||
          (audioUrl?.isNotEmpty ?? false) ||
          isClientTts);

  factory AppNotification.fromJson(Map<String, dynamic> j) => AppNotification(
        id: j['id'] as String,
        type: (j['type'] as String?) ?? 'text',
        title: j['title'] as String?,
        message: j['message'] as String?,
        priority: (j['priority'] as String?) ?? 'normal',
        presentation: (j['presentation'] as String?) ?? 'normal',
        voice: (j['voice'] as Map?)?.cast<String, dynamic>() ?? const {},
        playback: (j['playback'] as Map?)?.cast<String, dynamic>() ?? const {},
        actions: (j['actions'] as List?) ?? const [],
        correlationId: j['correlation_id'] as String?,
        threadId: j['thread_id'] as String?,
        groupKey: j['group_key'] as String?,
        expiresAt: j['expires_at'] != null
            ? DateTime.tryParse(j['expires_at'] as String)
            : null,
        readAt: j['read_at'] != null ? DateTime.tryParse(j['read_at'] as String) : null,
        createdAt: j['created_at'] != null
            ? DateTime.tryParse(j['created_at'] as String)
            : null,
      );
}
