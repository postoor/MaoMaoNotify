import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:maomao_client/api/api_client.dart';
import 'package:maomao_client/app_state.dart';
import 'package:maomao_client/models/app_notification.dart';
import 'package:maomao_client/settings/settings_store.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'fakes.dart';

http.Response _json(Object body, int status) =>
    http.Response(jsonEncode(body), status, headers: {'content-type': 'application/json'});

Future<SettingsStore> _settings() async {
  SharedPreferences.setMockInitialValues({});
  final s = await SettingsStore.load();
  await s.setTokens('acc', 'ref');
  return s;
}

AppNotification _voice(Map<String, dynamic> voice) => AppNotification.fromJson({
      'id': 'm', 'type': 'voice', 'message': 'body', 'voice': voice,
    });

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('playVoice mints a fresh signed URL by audio_id and plays it', () async {
    final settings = await _settings();
    String? requestedPath;
    final api = ApiClient(
      baseUrl: 'http://x',
      client: MockClient((req) async {
        requestedPath = req.url.path;
        return _json({'id': 'aud_1', 'url': 'http://fresh/url', 'content_type': 'audio/mpeg'}, 200);
      }),
    );
    final player = FakeAudioPlayer();
    final state = AppState(settings: settings, api: api, audioPlayer: player, speaker: FakeSpeaker());

    final result = await state.playVoice(_voice({'source': 'server_tts', 'audio_id': 'aud_1'}));

    expect(result.ok, isTrue);
    expect(requestedPath, '/api/v1/audio/aud_1');
    expect(player.played, ['http://fresh/url']); // fresh URL, not any stored one
  });

  test('playVoice falls back to the stored URL when the fresh fetch fails', () async {
    final settings = await _settings();
    final api = ApiClient(
      baseUrl: 'http://x',
      client: MockClient((req) async => _json({'error': {'code': 'not_found', 'message': 'x'}}, 404)),
    );
    final player = FakeAudioPlayer();
    final state = AppState(settings: settings, api: api, audioPlayer: player, speaker: FakeSpeaker());

    final result = await state
        .playVoice(_voice({'source': 'server_tts', 'audio_id': 'aud_1', 'audio_url': 'http://stored/url'}));

    expect(result.ok, isTrue);
    expect(player.played, ['http://stored/url']);
  });

  test('playVoice reports a message when the player cannot play', () async {
    final settings = await _settings();
    final api = ApiClient(
      baseUrl: 'http://x',
      client: MockClient((req) async => _json({'id': 'a', 'url': 'http://u', 'content_type': 'audio/mpeg'}, 200)),
    );
    final state = AppState(
      settings: settings, api: api,
      audioPlayer: FakeAudioPlayer(result: false), speaker: FakeSpeaker(),
    );

    final result = await state.playVoice(_voice({'source': 'server_tts', 'audio_id': 'a'}));

    expect(result.ok, isFalse);
    expect(result.message, isNotNull);
  });

  test('playVoice uses client TTS when there is no audio asset', () async {
    final settings = await _settings();
    final api = ApiClient(baseUrl: 'http://x', client: MockClient((req) async => _json({}, 200)));
    final speaker = FakeSpeaker();
    final state = AppState(
      settings: settings, api: api, audioPlayer: FakeAudioPlayer(), speaker: speaker,
    );

    final result = await state.playVoice(_voice({'source': 'client_tts', 'language': 'zh-TW'}));

    expect(result.ok, isTrue);
    expect(speaker.spoken, ['body']);
  });
}
