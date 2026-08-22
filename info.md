# Soniox

Speech-to-text and text-to-speech for Home Assistant powered by
[Soniox](https://soniox.com) — 60+ languages, low-latency streaming.

> **Disclaimer**: This is an unofficial project and is not affiliated with,
> endorsed by, or maintained by Soniox.

## Highlights

- Real-time STT (`stt-rt-v5`) — WebSocket streaming with final tokens.
- Async STT (`stt-async-v5`) — file upload + poll for higher-accuracy transcripts.
- TTS (`tts-rt-v2`) with 28 voices, every voice speaks every language.
- Per-call voice and audio-format overrides.
- No external Python dependencies — built on Home Assistant's bundled `aiohttp`.

## Quick setup

1. Install via HACS, restart Home Assistant.
2. **Settings → Devices & Services → Add Integration → Soniox**.
3. Paste an API key from [console.soniox.com](https://console.soniox.com).
4. **Settings → Voice assistants** → set both STT and TTS engines to **Soniox**.

Full docs and configuration options:
[github.com/kororos/ha-soniox](https://github.com/kororos/ha-soniox).
