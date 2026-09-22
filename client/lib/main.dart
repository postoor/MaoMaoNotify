import 'dart:io';

import 'package:battery_plus/battery_plus.dart';
import 'package:flutter/material.dart';
import 'package:sensors_plus/sensors_plus.dart';

import 'app_state.dart';
import 'models/app_notification.dart';
import 'presence/android_presence.dart';
import 'presence/motion_classifier.dart';
import 'presence/motion_sampler.dart';
import 'presence/observer.dart';
import 'push/unifiedpush_service.dart';
import 'settings/settings_store.dart';
import 'voice_alerts/voice_alerts_controller.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final settings = await SettingsStore.load();

  final observer = _buildObserver();
  final state = AppState(settings: settings, observer: observer);
  final voiceAlerts = VoiceAlertsController(
    initialEnabled: settings.voiceAlertsEnabled,
    onPersist: settings.setVoiceAlertsEnabled,
  );

  if (state.isLoggedIn && state.isPaired) {
    state.connect();
    state.startPresenceLoop();
    unawaitedSafe(state.loadNotifications());
    unawaitedSafe(_setupPush(state));
  }
  runApp(MaoMaoApp(state, voiceAlerts));
}

/// Android background push via UnifiedPush (self-hosted, §56 alt).
Future<void> _setupPush(AppState state) async {
  if (!Platform.isAndroid) return;
  final push = UnifiedPushService();
  await push.init();
  push.endpoints.listen((endpoint) => unawaitedSafe(state.registerPushEndpoint(endpoint)));
  push.wakeSignals.listen((_) => unawaitedSafe(state.handleWake()));
  await push.register();
}

/// On Android, feed the IMU classifier from sensors_plus and report battery.
/// Elsewhere, fall back to the desktop (Linux/logind) observer.
PresenceObserver? _buildObserver() {
  if (!Platform.isAndroid) return null; // AppState defaults to LinuxPresenceObserver
  final sampler = MotionSampler();
  sampler.start(
    accelerometerEventStream().map((e) => AccelSample(e.x, e.y, e.z)),
    gyro: gyroscopeEventStream().map((e) => AccelSample(e.x, e.y, e.z)),
  );
  final battery = Battery();
  return AndroidPresenceObserver(
    motion: () => sampler.currentMotion,
    battery: () async => {
      'level': await battery.batteryLevel,
      'charging': (await battery.batteryState) == BatteryState.charging,
    },
  );
}

void unawaitedSafe(Future<void> f) {
  f.catchError((_) {});
}

/// Format a notification's received time in the device's local timezone as
/// `YYYY-MM-DD HH:mm`. Returns '' when the timestamp is unknown.
String formatReceivedAt(DateTime? dt) {
  if (dt == null) return '';
  final t = dt.toLocal();
  String two(int v) => v.toString().padLeft(2, '0');
  return '${t.year}-${two(t.month)}-${two(t.day)} ${two(t.hour)}:${two(t.minute)}';
}

class MaoMaoApp extends StatelessWidget {
  const MaoMaoApp(this.state, this.voiceAlerts, {super.key});
  final AppState state;
  final VoiceAlertsController voiceAlerts;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'MaoMaoNotify',
      theme: ThemeData(colorSchemeSeed: Colors.indigo, useMaterial3: true),
      home: ListenableBuilder(
        listenable: state,
        builder: (context, _) => (state.isLoggedIn && state.isPaired)
            ? HomeScreen(state, voiceAlerts)
            : SetupScreen(state),
      ),
    );
  }
}

class SetupScreen extends StatefulWidget {
  const SetupScreen(this.state, {super.key});
  final AppState state;

  @override
  State<SetupScreen> createState() => _SetupScreenState();
}

class _SetupScreenState extends State<SetupScreen> {
  late final _server = TextEditingController(text: widget.state.settings.serverUrl);
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _code = TextEditingController();
  bool _busy = false;

  AppState get state => widget.state;

  Future<void> _run(Future<void> Function() action) async {
    setState(() => _busy = true);
    try {
      await state.setServerUrl(_server.text.trim());
      await action();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('MaoMaoNotify — Setup')),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: ListView(
            padding: const EdgeInsets.all(24),
            shrinkWrap: true,
            children: [
              TextField(
                controller: _server,
                decoration: const InputDecoration(labelText: 'Server URL'),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _email,
                decoration: const InputDecoration(labelText: 'Email'),
              ),
              TextField(
                controller: _password,
                obscureText: true,
                decoration: const InputDecoration(labelText: 'Password'),
              ),
              const SizedBox(height: 8),
              FilledButton(
                onPressed: _busy || state.isLoggedIn
                    ? null
                    : () => _run(() => state.login(_email.text.trim(), _password.text)),
                child: Text(state.isLoggedIn ? 'Logged in ✓' : 'Log in'),
              ),
              const Divider(height: 32),
              TextField(
                controller: _code,
                decoration: const InputDecoration(labelText: 'Pairing code (8 digits)'),
              ),
              const SizedBox(height: 8),
              FilledButton(
                onPressed: _busy || !state.isLoggedIn
                    ? null
                    : () => _run(() => state.pair(_code.text.trim())),
                child: const Text('Pair this device'),
              ),
              if (_busy)
                const Padding(
                  padding: EdgeInsets.only(top: 16),
                  child: LinearProgressIndicator(),
                ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  void dispose() {
    _server.dispose();
    _email.dispose();
    _password.dispose();
    _code.dispose();
    super.dispose();
  }
}

class HomeScreen extends StatelessWidget {
  const HomeScreen(this.state, this.voiceAlerts, {super.key});
  final AppState state;
  final VoiceAlertsController voiceAlerts;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('MaoMaoNotify — ${state.status}'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: state.loadNotifications),
          IconButton(icon: const Icon(Icons.logout), onPressed: state.logout),
        ],
      ),
      body: Column(
        children: [
          ListenableBuilder(
            listenable: voiceAlerts,
            builder: (context, _) => SwitchListTile(
              secondary: Icon(voiceAlerts.enabled ? Icons.volume_up : Icons.volume_off),
              title: const Text('Voice Alerts Mode'),
              subtitle: Text(voiceAlerts.enabled
                  ? 'ON — background voice service active'
                  : 'OFF — voice plays only while app is open'),
              value: voiceAlerts.enabled,
              onChanged: voiceAlerts.setEnabled,
            ),
          ),
          const Divider(height: 1),
          Expanded(
            child: state.notifications.isEmpty
                ? const Center(child: Text('No notifications yet.'))
                : ListView.separated(
                    itemCount: state.notifications.length,
                    separatorBuilder: (_, __) => const Divider(height: 1),
                    itemBuilder: (context, i) =>
                        _NotificationTile(state, state.notifications[i]),
                  ),
          ),
        ],
      ),
    );
  }
}

/// A notification row with interactive actions (§42–43). Buttons and text
/// inputs are disabled once the notification is resolved (§44).
class _NotificationTile extends StatefulWidget {
  const _NotificationTile(this.state, this.n);
  final AppState state;
  final AppNotification n;

  @override
  State<_NotificationTile> createState() => _NotificationTileState();
}

class _NotificationTileState extends State<_NotificationTile> {
  final Map<String, TextEditingController> _controllers = {};
  bool _playing = false;

  AppState get state => widget.state;
  AppNotification get n => widget.n;

  Future<void> _play() async {
    setState(() => _playing = true);
    final result = await state.playVoice(n);
    if (!mounted) return;
    setState(() => _playing = false);
    if (!result.ok) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(result.message ?? 'Playback failed')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final resolved = state.isResolved(n.id);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: Icon(n.isVoice ? Icons.record_voice_over : Icons.notifications),
            title: Text(n.title ?? '(no title)'),
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if ((n.message ?? '').isNotEmpty) Text(n.message!),
                if (n.createdAt != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: Text(
                      formatReceivedAt(n.createdAt),
                      style: Theme.of(context)
                          .textTheme
                          .bodySmall
                          ?.copyWith(color: Colors.grey),
                    ),
                  ),
              ],
            ),
            trailing: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(n.priority),
                if (n.hasPlayableVoice)
                  _playing
                      ? const Padding(
                          padding: EdgeInsets.all(12),
                          child: SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          ),
                        )
                      : IconButton(
                          icon: const Icon(Icons.play_circle_fill),
                          tooltip: 'Play voice',
                          onPressed: _play,
                        ),
              ],
            ),
          ),
          if (n.actions.isNotEmpty)
            Wrap(
              spacing: 8,
              runSpacing: 8,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [for (final a in n.actions) _action(a as Map, resolved)],
            ),
          if (resolved)
            const Padding(
              padding: EdgeInsets.only(top: 4),
              child: Text('resolved', style: TextStyle(color: Colors.grey)),
            ),
        ],
      ),
    );
  }

  Widget _action(Map a, bool resolved) {
    final id = a['id'] as String;
    final label = (a['label'] as String?) ?? id;
    if (a['type'] == 'text_input') {
      final controller = _controllers.putIfAbsent(id, TextEditingController.new);
      return SizedBox(
        width: 260,
        child: Row(
          children: [
            Expanded(
              child: TextField(
                controller: controller,
                enabled: !resolved,
                decoration: InputDecoration(
                  isDense: true,
                  labelText: label,
                  hintText: a['placeholder'] as String?,
                ),
              ),
            ),
            IconButton(
              icon: const Icon(Icons.send),
              onPressed: resolved
                  ? null
                  : () => state.respond(n, id, value: controller.text),
            ),
          ],
        ),
      );
    }
    return FilledButton(
      onPressed: resolved ? null : () => state.respond(n, id),
      child: Text(label),
    );
  }

  @override
  void dispose() {
    for (final c in _controllers.values) {
      c.dispose();
    }
    super.dispose();
  }
}
