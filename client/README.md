# MaoMaoNotify Client

Single Flutter repository targeting **Android / macOS / Linux**. Platform-
specific behavior (presence sensors, system TTS, foreground audio, tray/menu-bar
integration) goes through Flutter Platform Channels / plugins.

## lib/ layout

| package        | responsibility |
|----------------|----------------|
| `api/`         | REST client for the server API |
| `auth/`        | login, token storage, refresh |
| `models/`      | shared data models |
| `notification/`| notification display + history |
| `presence/`    | observation reporting (no self-declared "active") |
| `websocket/`   | persistent WS: delivery, ACK, read sync, actions |
| `audio/`       | audio playback (agent audio / server TTS assets) |
| `tts/`         | client system TTS |
| `settings/`    | user/device preferences UI + storage |
| `ui/`          | screens & widgets |

## Platform notes

- **macOS**: menu-bar app + LaunchAgent background component.
- **Linux**: tray app + `systemd --user` service; presence via systemd-logind /
  DBus (Wayland-aware, no X11-only global input hook).
- **Android**: FCM as wake signal only (payload fetched from server); optional
  Voice Alerts Mode uses a foreground media service; IMU motion is classified
  on-device (no raw sensor stream sent).

## Bootstrap

The platform runner directories (`android/`, `macos/`, `linux/`) are placeholders.
Generate them with:

```bash
cd client
flutter create --platforms=android,macos,linux --project-name maomao_client .
```

Skeleton only — no app code yet.
