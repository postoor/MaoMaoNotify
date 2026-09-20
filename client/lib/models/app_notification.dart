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

  bool get isVoice => type == 'voice';
  bool get isSilent => presentation == 'silent';
  bool get isRead => readAt != null;

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
      );
}
