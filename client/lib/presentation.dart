import 'dart:io';

import 'audio/audio_player.dart';
import 'notification/desktop_notifier.dart';
import 'notification/notifier.dart';
import 'tts/speaker.dart';

/// Pick the platform implementations for presentation.
Speaker createSpeaker() => Platform.isAndroid ? AndroidSpeaker() : DesktopSpeaker();

Notifier createNotifier() => Platform.isAndroid ? AndroidNotifier() : DesktopNotifier();

AudioPlayer createAudioPlayer() =>
    Platform.isAndroid ? AndroidAudioPlayer() : DesktopAudioPlayer();
