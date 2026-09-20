// Live end-to-end smoke for the desktop client, driven headlessly (no GUI).
// Exercises the REAL stack: pairing redeem (HTTP) -> WebSocket connect -> a
// notification pushed by an agent -> received over WS -> desktop popup + TTS.
//
// Run: dart run tool/live_smoke.dart
// Env: SERVER_URL, PAIRING_CODE, AGENT_TOKEN
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:maomao_client/api/api_client.dart';
import 'package:maomao_client/notification/desktop_notifier.dart';
import 'package:maomao_client/tts/client_tts.dart';
import 'package:maomao_client/websocket/ws_client.dart';

Future<void> main() async {
  final server = Platform.environment['SERVER_URL'] ?? 'http://localhost:8055';
  final code = Platform.environment['PAIRING_CODE'];
  final agentToken = Platform.environment['AGENT_TOKEN'];
  if (code == null || agentToken == null) {
    stderr.writeln('Set PAIRING_CODE and AGENT_TOKEN');
    exitCode = 2;
    return;
  }

  final api = ApiClient(baseUrl: server);
  stdout.writeln('1) redeem pairing …');
  final dev = await api.redeemPairing(
    code: code,
    platform: 'linux',
    detectedName: Platform.localHostname,
    capabilities: const ['text_notification', 'client_tts', 'presence'],
  );
  stdout.writeln('   device_id=${dev.deviceId}');

  stdout.writeln('2) connect WebSocket …');
  final ws = WsClient(baseUrl: server, deviceToken: dev.deviceToken);
  final received = ws.notifications.first; // subscribe before connect
  ws.connect();
  await Future<void>.delayed(const Duration(milliseconds: 1500));

  stdout.writeln('3) agent sends a voice notification …');
  final resp = await http.post(
    Uri.parse('$server/api/v1/notifications'),
    headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer $agentToken'},
    body: jsonEncode({
      'title': 'Claude Code',
      'type': 'voice',
      'priority': 'high',
      'voice': {'source': 'client_tts', 'language': 'zh-TW'},
      'content': {'text': '部署完成，這是 live 端到端測試'},
    }),
  );
  stdout.writeln('   POST /notifications -> ${resp.statusCode}');
  if (resp.statusCode != 201) {
    stderr.writeln('   body: ${resp.body}');
    exitCode = 1;
    return;
  }

  stdout.writeln('4) await delivery over WebSocket …');
  final n = await received.timeout(const Duration(seconds: 10));
  stdout.writeln('   RECEIVED id=${n.id} title="${n.title}" type=${n.type}');
  ws.ack(n.id, status: 'delivered');

  stdout.writeln('5) present (desktop popup + client TTS) …');
  final shown = await DesktopNotifier().show(n);
  stdout.writeln('   notify-send shown=$shown');
  final spoke = await ClientTts().speak(n.message ?? '測試', language: 'zh-TW');
  stdout.writeln('   client TTS spoke=$spoke');
  if (shown) ws.ack(n.id, status: 'displayed');
  if (spoke) ws.ack(n.id, status: 'played');

  await Future<void>.delayed(const Duration(milliseconds: 500));
  await ws.close();
  api.close();
  stdout.writeln('OK: full client stack verified over the wire.');
}
