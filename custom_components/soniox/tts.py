"""Soniox text-to-speech platform."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import aiohttp

from homeassistant.components.tts import (
    ATTR_AUDIO_OUTPUT,
    ATTR_PREFERRED_FORMAT,
    ATTR_PREFERRED_SAMPLE_RATE,
    ATTR_VOICE,
    TextToSpeechEntity,
    TtsAudioType,
    TTSAudioRequest,
    TTSAudioResponse,
    Voice,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SonioxConfigEntry
from .const import (
    CONF_API_KEY,
    CONF_REGION,
    CONF_TTS_AUDIO_FORMAT,
    CONF_TTS_LANGUAGE,
    CONF_TTS_MODEL,
    CONF_TTS_SAMPLE_RATE,
    CONF_TTS_VOICE,
    DEFAULT_REGION,
    DEFAULT_TTS_AUDIO_FORMAT,
    DEFAULT_TTS_LANGUAGE,
    DEFAULT_TTS_MODEL,
    DEFAULT_TTS_SAMPLE_RATE,
    DEFAULT_TTS_VOICE,
    DOMAIN,
    REGION_LABELS,
    SUPPORTED_LANGUAGES,
    TTS_VOICES,
)

_LOGGER = logging.getLogger(__name__)

# Map Soniox audio_format → file extension HA expects back.
_EXTENSION_BY_FORMAT = {
    "mp3": "mp3",
    "wav": "wav",
    "pcm_s16le": "pcm",
}

# Assist satellites can start playback as soon as the first PCM/WAV chunk
# arrives. MP3 needs a complete frame sequence and is buffered as a file.
_STREAMABLE_FORMATS = {"wav", "pcm_s16le"}
_STREAM_DEFAULT_FORMAT = "wav"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SonioxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Register the Soniox TTS entity for this config entry."""
    async_add_entities([SonioxTTSEntity(entry)])


class SonioxTTSEntity(TextToSpeechEntity):
    """Soniox TTS — full-message REST path, streaming WebSocket path."""

    _attr_has_entity_name = True
    _attr_name = "Text-to-Speech"

    def __init__(self, entry: SonioxConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}-tts"
        region = entry.data.get(CONF_REGION, DEFAULT_REGION)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Soniox ({REGION_LABELS.get(region, REGION_LABELS[DEFAULT_REGION])})",
            manufacturer="Soniox",
            model="Speech AI",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def default_language(self) -> str:
        return self._entry.options.get(CONF_TTS_LANGUAGE, DEFAULT_TTS_LANGUAGE)

    @property
    def supported_languages(self) -> list[str]:
        return SUPPORTED_LANGUAGES

    @property
    def supported_options(self) -> list[str]:
        return [
            ATTR_VOICE,
            ATTR_AUDIO_OUTPUT,
            ATTR_PREFERRED_FORMAT,
            ATTR_PREFERRED_SAMPLE_RATE,
        ]

    @property
    def default_options(self) -> dict[str, Any]:
        audio_format = self._entry.options.get(
            CONF_TTS_AUDIO_FORMAT, DEFAULT_TTS_AUDIO_FORMAT
        )
        if audio_format not in _STREAMABLE_FORMATS:
            audio_format = _STREAM_DEFAULT_FORMAT
        return {
            ATTR_VOICE: self._entry.options.get(CONF_TTS_VOICE, DEFAULT_TTS_VOICE),
            ATTR_AUDIO_OUTPUT: audio_format,
            # Home Assistant's tts.speak URL uses preferred_format (default mp3).
            # Matching wav here skips ffmpeg remux so the media player can
            # start playing chunks as soon as Soniox produces them.
            ATTR_PREFERRED_FORMAT: "wav" if audio_format == "pcm_s16le" else audio_format,
        }

    @callback
    def async_get_supported_voices(self, language: str) -> list[Voice]:
        # Soniox voices speak every supported language, so the same list applies.
        return [Voice(voice_id=v, name=v) for v in TTS_VOICES]

    async def async_get_tts_audio(
        self, message: str, language: str, options: dict[str, Any]
    ) -> TtsAudioType:
        """One-shot synthesis via the same WebSocket stream as Assist / tts.speak.

        Home Assistant still needs a complete buffer for this method, so this
        path cannot start playback early. tts.speak and Assist use
        async_stream_tts_audio instead.
        """

        async def _one_message() -> AsyncGenerator[str]:
            yield message

        response = await self.async_stream_tts_audio(
            TTSAudioRequest(
                language=language,
                options=options,
                message_gen=_one_message(),
            )
        )
        audio = b"".join([chunk async for chunk in response.data_gen])
        if not audio:
            raise HomeAssistantError("Soniox TTS returned no audio")
        return response.extension, audio

    async def async_stream_tts_audio(
        self, request: TTSAudioRequest
    ) -> TTSAudioResponse:
        """Streaming synthesis via the Soniox TTS WebSocket.

        Opens the socket and sends the stream config immediately so the
        handshake overlaps with Home Assistant starting playback. Audio
        chunks are then yielded as soon as Soniox produces them.
        """
        audio_format = self._resolve_stream_format(request.options)
        _LOGGER.debug(
            "Soniox TTS path: WebSocket stream (format=%s)", audio_format
        )
        extension = _EXTENSION_BY_FORMAT.get(audio_format, "wav")
        session = async_get_clientsession(self.hass)
        config = self._stream_config(request, audio_format)
        try:
            ws = await session.ws_connect(
                self._entry.runtime_data.tts_websocket_url,
                heartbeat=30,
                max_msg_size=0,
            )
        except aiohttp.ClientError as err:
            raise HomeAssistantError(
                f"Soniox TTS streaming connection failed: {err}"
            ) from err
        try:
            await ws.send_json(config)
        except aiohttp.ClientError as err:
            await ws.close()
            raise HomeAssistantError(
                f"Soniox TTS streaming connection failed: {err}"
            ) from err
        return TTSAudioResponse(
            extension=extension,
            data_gen=self._stream_audio(ws, request, config["stream_id"]),
        )

    def _resolve_stream_format(self, options: dict[str, Any]) -> str:
        """Pick a chunk-friendly format so Assist can play audio immediately.

        The entity default is mp3 (good for tts.speak files). Assist merges
        that default into every request, which would force the WebSocket onto
        a buffered container. Prefer wav/pcm instead.
        """
        preferred = options.get(ATTR_PREFERRED_FORMAT)
        if preferred in ("wav", "pcm", "pcm_s16le"):
            return "wav" if preferred == "pcm" else preferred
        explicit = options.get(ATTR_AUDIO_OUTPUT)
        if explicit in _STREAMABLE_FORMATS:
            return explicit
        return _STREAM_DEFAULT_FORMAT

    def _resolve_sample_rate(self, options: dict[str, Any]) -> int:
        preferred = options.get(ATTR_PREFERRED_SAMPLE_RATE)
        if preferred:
            try:
                return int(preferred)
            except (TypeError, ValueError):
                pass
        return int(
            self._entry.options.get(CONF_TTS_SAMPLE_RATE, DEFAULT_TTS_SAMPLE_RATE)
        )

    def _stream_config(
        self, request: TTSAudioRequest, audio_format: str
    ) -> dict[str, Any]:
        model = self._entry.options.get(CONF_TTS_MODEL, DEFAULT_TTS_MODEL)
        config: dict[str, Any] = {
            "api_key": self._entry.data[CONF_API_KEY],
            "model": model,
            "language": (request.language or self.default_language)
            .split("-", 1)[0]
            .lower(),
            "voice": request.options.get(
                ATTR_VOICE,
                self._entry.options.get(CONF_TTS_VOICE, DEFAULT_TTS_VOICE),
            ),
            "audio_format": audio_format,
            "stream_id": uuid.uuid4().hex,
        }
        if audio_format.startswith("pcm") or audio_format == "wav":
            config["sample_rate"] = self._resolve_sample_rate(request.options)
        if str(model).startswith("tts-rt-v2"):
            config["reduce_silence"] = True
        return config

    async def _stream_audio(
        self,
        ws: aiohttp.ClientWebSocketResponse,
        request: TTSAudioRequest,
        stream_id: str,
    ) -> AsyncGenerator[bytes]:
        """Yield decoded audio chunks from an already-configured WebSocket."""

        async def pump_text() -> None:
            async for chunk in request.message_gen:
                if chunk:
                    await ws.send_json(
                        {"text": chunk, "text_end": False, "stream_id": stream_id}
                    )
            await ws.send_json({"text": "", "text_end": True, "stream_id": stream_id})

        pump_task = asyncio.create_task(pump_text())
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    payload = json.loads(msg.data)
                    if err := payload.get("error_code"):
                        _LOGGER.error(
                            "Soniox TTS error %s: %s",
                            err,
                            payload.get("error_message"),
                        )
                        break
                    if payload.get("stream_id") not in (None, stream_id):
                        continue
                    if audio_b64 := payload.get("audio"):
                        yield base64.b64decode(audio_b64)
                    if payload.get("terminated") or payload.get("audio_end"):
                        break
                elif msg.type in (
                    aiohttp.WSMsgType.CLOSED,
                    aiohttp.WSMsgType.ERROR,
                ):
                    break
        finally:
            pump_task.cancel()
            try:
                await pump_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            if not ws.closed:
                await ws.close()
