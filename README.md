# Soniox for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Validate](https://github.com/kororos/ha-soniox/actions/workflows/validate.yml/badge.svg)](https://github.com/kororos/ha-soniox/actions/workflows/validate.yml)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/kororos/ha-soniox)](https://github.com/kororos/ha-soniox/releases)
[![License: MIT](https://img.shields.io/github/license/kororos/ha-soniox)](https://github.com/kororos/ha-soniox/blob/main/LICENSE)

A custom Home Assistant integration that exposes [Soniox](https://soniox.com)
as both a **speech-to-text** and **text-to-speech** provider, ready to plug
into the Assist voice pipeline.

> **Disclaimer**: This is an unofficial project and is not affiliated with,
> endorsed by, or maintained by Soniox. The Soniox name and logo are used
> with permission for the purpose of this community integration.

- **STT (realtime)** — `stt-rt-v5` over WebSocket. Supports 60+ languages
  and sends low-latency final tokens as the user speaks.
- **STT (async)** — `stt-async-v5` via the Files + Transcriptions REST API.
  Buffers the utterance, uploads it, and polls for a higher-accuracy transcript.
- **TTS** — `tts-rt-v2` voices, both as a one-shot REST call and as a
  streaming WebSocket session (so LLM-generated text can start speaking before
  it's fully written).

## Installation

### Via HACS (recommended)

1. Open **HACS → Integrations** in Home Assistant.
2. Click the **⋮** menu → **Custom repositories**.
3. Add `https://github.com/kororos/ha-soniox` with category **Integration**.
4. Search for **Soniox**, install, then restart Home Assistant.
5. **Settings → Devices & Services → Add Integration → Soniox**.
6. Paste an API key from [console.soniox.com](https://console.soniox.com).

### Manual

Copy `custom_components/soniox/` into your Home Assistant `config/custom_components/`
directory, restart, and follow steps 5–6 above.

## Configuration

Open the integration's **Configure** screen to set defaults:

| Option              | Default      | Notes                                                                |
| ------------------- | ------------ | -------------------------------------------------------------------- |
| Realtime STT model  | `stt-rt-v5`  | WebSocket streaming. Used by the `Speech-to-Text` entity.            |
| Async STT model     | `stt-async-v5` | File upload + poll. Used by the `Speech-to-Text (Async)` entity.   |
| TTS model           | `tts-rt-v2`  | Soniox real-time TTS model.                                          |
| Default TTS voice   | `Maya`       | Any voice from the Soniox catalog (see below).                       |
| Default TTS language| `en`         | Two-letter ISO code.                                                 |
| TTS audio format    | `mp3`        | `mp3`, `wav`, or `pcm_s16le`.                                        |
| TTS sample rate     | `24000`      | Used only for raw/wav formats.                                       |

Per-service-call overrides:

- `voice` — any voice name (Maya, Adrian, Kenji, Sofia, …).
- `audio_output` — `mp3`, `wav`, or `pcm_s16le`.

## Use it in the Assist pipeline

**Settings → Voice assistants → Assistant → Add assistant**, then pick the
`Soniox Speech-to-Text` (or `Speech-to-Text (Async)`) entity and the
`Soniox` TTS entity. Use realtime STT for Assist; async STT is slower but
typically more accurate on a complete recording.

> **Note**: To use the browser mic icon on your laptop, Home Assistant must be
> served over HTTPS (browsers block microphone access on plain HTTP from
> non-localhost origins). The Home Assistant mobile apps don't have this
> restriction.

## Supported voices

`Maya`, `Daniel`, `Noah`, `Nina`, `Emma`, `Jack`, `Adrian`, `Claire`,
`Grace`, `Owen`, `Mina`, `Kenji`, `Rafael`, `Mateo`, `Lucia`, `Sofia`,
`Oliver`, `Arthur`, `Isla`, `Victoria`, `Cooper`, `Mason`, `Ruby`,
`Elise`, `Arjun`, `Rohan`, `Priya`, `Meera`. All voices speak all
supported languages.

## Issues

Please file bugs and feature requests at
[github.com/kororos/ha-soniox/issues](https://github.com/kororos/ha-soniox/issues).

## License

MIT — see [LICENSE](LICENSE).
