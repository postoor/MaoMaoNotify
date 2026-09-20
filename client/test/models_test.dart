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

  test('AppNotification defaults are safe', () {
    final n = AppNotification.fromJson({'id': 'msg_2'});
    expect(n.type, 'text');
    expect(n.priority, 'normal');
    expect(n.actions, isEmpty);
  });
}
