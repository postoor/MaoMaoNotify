# Piper TTS container (optional)

Local TTS provider for the `PiperProvider`. Enable with the `tts` compose
profile:

```bash
docker compose --profile tts up piper
```

Add a `Dockerfile` here that runs a Piper HTTP endpoint (default port 10200) and
mount voice models. Configure `piper.model_path` / voice in server TTS config.
Skeleton only.
