"""Constants for the Soniox integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "soniox"

# Config / options keys
CONF_API_KEY: Final = "api_key"
CONF_STT_MODEL: Final = "stt_model"
CONF_STT_ASYNC_MODEL: Final = "stt_async_model"
CONF_TTS_MODEL: Final = "tts_model"
CONF_TTS_VOICE: Final = "tts_voice"
CONF_TTS_LANGUAGE: Final = "tts_language"
CONF_TTS_AUDIO_FORMAT: Final = "tts_audio_format"
CONF_TTS_SAMPLE_RATE: Final = "tts_sample_rate"

# Soniox endpoints
STT_API_BASE_URL: Final = "https://api.soniox.com"
STT_FILES_URL: Final = f"{STT_API_BASE_URL}/v1/files"
STT_TRANSCRIPTIONS_URL: Final = f"{STT_API_BASE_URL}/v1/transcriptions"
STT_WEBSOCKET_URL: Final = "wss://stt-rt.soniox.com/transcribe-websocket"
TTS_REST_URL: Final = "https://tts-rt.soniox.com/tts"
TTS_WEBSOCKET_URL: Final = "wss://tts-rt.soniox.com/tts-websocket"
TTS_MODELS_URL: Final = "https://api.soniox.com/v1/tts-models"

# Models (https://soniox.com/docs/stt/models, https://soniox.com/docs/tts/models)
STT_REALTIME_MODELS: Final = ["stt-rt-v5"]
STT_ASYNC_MODELS: Final = ["stt-async-v5"]
TTS_MODELS: Final = ["tts-rt-v2", "tts-rt-v1"]

# Defaults
DEFAULT_STT_MODEL: Final = "stt-rt-v5"
DEFAULT_STT_ASYNC_MODEL: Final = "stt-async-v5"
DEFAULT_TTS_MODEL: Final = "tts-rt-v2"
DEFAULT_TTS_VOICE: Final = "Maya"
DEFAULT_TTS_LANGUAGE: Final = "en"
DEFAULT_TTS_AUDIO_FORMAT: Final = "mp3"
DEFAULT_TTS_SAMPLE_RATE: Final = 24000

# Built-in voice list (https://soniox.com/docs/tts/models — all voices speak all languages).
TTS_VOICES: Final = [
    "Maya", "Daniel", "Noah", "Nina", "Emma", "Jack", "Adrian", "Claire",
    "Grace", "Owen", "Mina", "Kenji", "Rafael", "Mateo", "Lucia", "Sofia",
    "Oliver", "Arthur", "Isla", "Victoria", "Cooper", "Mason", "Ruby",
    "Elise", "Arjun", "Rohan", "Priya", "Meera",
]

# Curated subset of the 60+ languages Soniox advertises. Used as the
# advertised supported_languages list for both STT and TTS — the Soniox
# models actually handle far more codes, but Home Assistant prefers a
# concrete list it can match assist-pipeline languages against.
SUPPORTED_LANGUAGES: Final = [
    "af", "ar", "az", "be", "bg", "bn", "bs", "ca", "cs", "cy", "da", "de",
    "el", "en", "es", "et", "eu", "fa", "fi", "fr", "gl", "gu", "he", "hi",
    "hr", "hu", "hy", "id", "is", "it", "ja", "kk", "kn", "ko", "lt", "lv",
    "mi", "mk", "ml", "mn", "mr", "ms", "ne", "nl", "no", "pa", "pl", "ps",
    "pt", "ro", "ru", "sk", "sl", "sq", "sr", "sv", "sw", "ta", "te", "th",
    "tl", "tr", "uk", "ur", "uz", "vi", "zh",
]


def is_async_stt_model(model: str) -> bool:
    """Return True if the model uses the async (file) STT API."""
    return "async" in model
