import 'package:flutter_test/flutter_test.dart';
import 'package:maomao_client/models/app_notification.dart';
import 'package:maomao_client/models/observation.dart';
import 'package:maomao_client/models/token_pair.dart';

void main() {
  test('TokenPair round-trips', () {
    final pair = TokenPair.fromJson(
      {'access_token': 'a', 'refresh_token': 'r', 'token_type': 'bearer'},
    );
    expect(pair.accessToken, 'a');
    expect(pair.refreshToken, 'r');
    expect(pair.toJson()['access_token'], 'a');
  });

  test('Observation.toJson uses server snake_case keys and omits nulls', () {
    final obs = Observation(
      screen: 'on', locked: false, lastInteractionMs: 5000, appState: 'foreground',
    );
    final j = obs.toJson();
    expect(j['last_interaction_ms'], 5000);
    expect(j['app_state'], 'foreground');
    expect(j['locked'], false);
    expect(j.containsKey('motion'), isFalse); // null omitted
    expect(j['audio'], isA<Map>());
  });

  test('AppNotification parses WS/REST payload', () {
    final n = AppNotification.fromJson({
      'id': 'msg_1',
      'type': 'voice',
      'title': 'Claude',
      'message': '部署完成',
      'priority': 'high',
      'presentation': 'silent',
      'voice': {'source': 'client_tts', 'language': 'zh-TW'},
      'correlation_id': 'deploy_1',
    });
    expect(n.id, 'msg_1');
    expect(n.isVoice, isTrue);
    expect(n.isSilent, isTrue);
    expect(n.voice['source'], 'client_tts');
    expect(n.correlationId, 'deploy_1');
  });

  test('AppNotification parses created_at and exposes voice helpers', () {
    final n = AppNotification.fromJson({
      'id': 'msg_3',
      'type': 'voice',
      'message': '部署完成',
      'voice': {'source': 'server_tts', 'audio_id': 'aud_1', 'audio_url': 'http://m/aud_1?sig=x'},
      'created_at': '2026-09-22T03:04:05Z',
    });
    expect(n.createdAt, DateTime.utc(2026, 9, 22, 3, 4, 5));
    expect(n.audioId, 'aud_1');
    expect(n.audioUrl, 'http://m/aud_1?sig=x');
    expect(n.hasPlayableVoice, isTrue);
    expect(n.isClientTts, isFalse);
  });

  test('client_tts voice is playable without an audio asset', () {
    final n = AppNotification.fromJson({
      'id': 'msg_4', 'type': 'voice', 'message': 'hi',
      'voice': {'source': 'client_tts', 'language': 'zh-TW'},
    });
    expect(n.hasPlayableVoice, isTrue);
    expect(n.isClientTts, isTrue);
    expect(n.audioId, isNull);
  });

  test('a plain text notification has no playable voice', () {
    final n = AppNotification.fromJson({'id': 'msg_5', 'type': 'text', 'message': 'hi'});
    expect(n.hasPlayableVoice, isFalse);
    expect(n.createdAt, isNull);
  });

  test('AppNotification defaults are safe', () {
    final n = AppNotification.fromJson({'id': 'msg_2'});
    expect(n.type, 'text');
    expect(n.priority, 'normal');
    expect(n.actions, isEmpty);
  });
}
