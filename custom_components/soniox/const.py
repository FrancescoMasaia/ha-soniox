"""Constants for the Soniox integration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Final

DOMAIN: Final = "soniox"

# Config / options keys
CONF_API_KEY: Final = "api_key"
CONF_REGION: Final = "region"
CONF_STT_MODEL: Final = "stt_model"
CONF_STT_ASYNC_MODEL: Final = "stt_async_model"
CONF_TTS_MODEL: Final = "tts_model"
CONF_TTS_VOICE: Final = "tts_voice"
CONF_TTS_LANGUAGE: Final = "tts_language"
CONF_TTS_AUDIO_FORMAT: Final = "tts_audio_format"
CONF_TTS_SAMPLE_RATE: Final = "tts_sample_rate"
CONF_STT_ENDPOINT_DETECTION: Final = "stt_endpoint_detection"
CONF_STT_ENDPOINT_LATENCY_LEVEL: Final = "stt_endpoint_latency_level"
CONF_STT_ENDPOINT_SENSITIVITY: Final = "stt_endpoint_sensitivity"
CONF_STT_MAX_ENDPOINT_DELAY_MS: Final = "stt_max_endpoint_delay_ms"
CONF_STT_CONTEXT: Final = "stt_context"
CONF_STT_CONTEXT_HOME: Final = "stt_context_home"

# Regional deployments (https://soniox.com/docs/data-residency)
REGION_US: Final = "us"
REGION_EU: Final = "eu"
REGION_JP: Final = "jp"
DEFAULT_REGION: Final = REGION_US

# host family → (api, stt-rt, tts-rt)
_REGION_HOSTS: Final = {
    REGION_US: ("api.soniox.com", "stt-rt.soniox.com", "tts-rt.soniox.com"),
    REGION_EU: ("api.eu.soniox.com", "stt-rt.eu.soniox.com", "tts-rt.eu.soniox.com"),
    REGION_JP: ("api.jp.soniox.com", "stt-rt.jp.soniox.com", "tts-rt.jp.soniox.com"),
}

REGION_LABELS: Final = {
    REGION_US: "United States",
    REGION_EU: "European Union",
    REGION_JP: "Japan",
}


@dataclass(frozen=True)
class SonioxEndpoints:
    """Resolved REST and WebSocket URLs for a Soniox region."""

    region: str
    stt_files_url: str
    stt_transcriptions_url: str
    stt_websocket_url: str
    tts_rest_url: str
    tts_websocket_url: str
    tts_models_url: str


def endpoints_for_region(region: str) -> SonioxEndpoints:
    """Build service URLs for a regional Soniox deployment."""
    api, stt_rt, tts_rt = _REGION_HOSTS.get(region, _REGION_HOSTS[DEFAULT_REGION])
    return SonioxEndpoints(
        region=region if region in _REGION_HOSTS else DEFAULT_REGION,
        stt_files_url=f"https://{api}/v1/files",
        stt_transcriptions_url=f"https://{api}/v1/transcriptions",
        stt_websocket_url=f"wss://{stt_rt}/transcribe-websocket",
        tts_rest_url=f"https://{tts_rt}/tts",
        tts_websocket_url=f"wss://{tts_rt}/tts-websocket",
        tts_models_url=f"https://{api}/v1/tts-models",
    )

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
DEFAULT_TTS_AUDIO_FORMAT: Final = "wav"
DEFAULT_TTS_SAMPLE_RATE: Final = 24000
# Soniox recommended starting point for responsive voice assistants.
# https://soniox.com/docs/stt/rt/endpoint-detection
DEFAULT_STT_ENDPOINT_DETECTION: Final = True
DEFAULT_STT_ENDPOINT_LATENCY_LEVEL: Final = 2
DEFAULT_STT_ENDPOINT_SENSITIVITY: Final = 0.3
DEFAULT_STT_MAX_ENDPOINT_DELAY_MS: Final = 1500
DEFAULT_STT_CONTEXT_HOME: Final = True
STT_ENDPOINT_TOKEN: Final = "<end>"
# Soniox rejects context above ~10,000 characters; keep a safety margin.
STT_CONTEXT_CHAR_LIMIT: Final = 9000

# Bias realtime/async STT toward typical Home Assistant voice commands.
# Sent as Soniox structured context (general + terms + this text).
# https://soniox.com/docs/stt/concepts/context
DEFAULT_STT_CONTEXT: Final = (
    "Una persona parla all'assistente vocale di casa. "
    "Comandi brevi su luci, musica, clima e tapparelle."
)

# Fallback only when the house has no named rooms or devices yet.
DEFAULT_STT_CONTEXT_TERMS: Final = [
    "Home Assistant",
    "cucina",
    "soggiorno",
    "camera",
    "tapparelle",
    "termostato",
    "aspirapolvere",
]

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


def build_stt_context(
    raw: str | None,
    language: str,  # noqa: ARG001 — kept for call-site compatibility
    extra_terms: list[str] | None = None,
    extra_general: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Build the Soniox structured context sent with each STT session.

    A JSON object with ``general`` / ``text`` / ``terms`` replaces the built-in
    hints. Anything else is used as the ``text`` section on top of the default
    home-assistant domain and vocabulary. When house names are available they
    replace the generic term list instead of being merged with it.
    """
    text = (raw if raw is not None else DEFAULT_STT_CONTEXT).strip()
    context: dict[str, Any] | None = None
    if text.startswith("{") and text.endswith("}"):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            inner = parsed.get("context")
            if isinstance(inner, dict):
                context = dict(inner)
            elif any(
                key in parsed
                for key in ("general", "text", "terms", "translation_terms")
            ):
                context = dict(parsed)

    if context is None:
        general: list[dict[str, str]] = [
            {"key": "domain", "value": "Assistente vocale di casa"},
            {"key": "setting", "value": "Home Assistant"},
            {"key": "language", "value": "italiano"},
            {
                "key": "instructions",
                "value": "Trascrivi il comando in italiano, compresi i nomi di stanze e dispositivi.",
            },
        ]
        context = {
            "general": general,
            "terms": list(extra_terms or DEFAULT_STT_CONTEXT_TERMS),
        }
        if text:
            context["text"] = text

    if extra_general:
        existing_general = list(context.get("general") or [])
        existing_keys = {
            item.get("key")
            for item in existing_general
            if isinstance(item, dict)
        }
        for item in extra_general:
            if item.get("key") not in existing_keys:
                existing_general.append(item)
        context["general"] = existing_general

    if extra_terms:
        # Real rooms/devices already describe this house — drop generic fillers.
        context["terms"] = list(extra_terms)

    return _trim_stt_context(context)


def _trim_stt_context(context: dict[str, Any]) -> dict[str, Any]:
    """Drop trailing terms if the payload would exceed Soniox's size limit."""
    terms = list(context.get("terms") or [])
    while terms and len(json.dumps(context, ensure_ascii=False)) > STT_CONTEXT_CHAR_LIMIT:
        terms.pop()
        if terms:
            context["terms"] = terms
        else:
            context.pop("terms", None)
    return context
