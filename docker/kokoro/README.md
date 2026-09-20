# Kokoro TTS container (optional)

Local TTS provider for the `KokoroProvider`. Enable with the `tts` compose
profile:

```bash
docker compose --profile tts up kokoro
```

Add a `Dockerfile` here that serves the Kokoro HTTP endpoint (default port
8880). Configure `kokoro.endpoint` in server TTS config. Skeleton only.
