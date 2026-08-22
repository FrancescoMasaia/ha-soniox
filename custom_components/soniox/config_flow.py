"""Config flow for the Soniox integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_API_KEY,
    CONF_STT_ASYNC_MODEL,
    CONF_STT_MODEL,
    CONF_TTS_AUDIO_FORMAT,
    CONF_TTS_LANGUAGE,
    CONF_TTS_MODEL,
    CONF_TTS_SAMPLE_RATE,
    CONF_TTS_VOICE,
    DEFAULT_STT_ASYNC_MODEL,
    DEFAULT_STT_MODEL,
    DEFAULT_TTS_AUDIO_FORMAT,
    DEFAULT_TTS_LANGUAGE,
    DEFAULT_TTS_MODEL,
    DEFAULT_TTS_SAMPLE_RATE,
    DEFAULT_TTS_VOICE,
    DOMAIN,
    STT_ASYNC_MODELS,
    STT_REALTIME_MODELS,
    SUPPORTED_LANGUAGES,
    TTS_MODELS,
    TTS_MODELS_URL,
    TTS_VOICES,
)

_LOGGER = logging.getLogger(__name__)

TTS_AUDIO_FORMATS = ["mp3", "wav", "pcm_s16le"]
TTS_SAMPLE_RATES = [8000, 16000, 24000, 44100, 48000]


def _model_options(
    choices: list[str], current: str | None
) -> list[SelectOptionDict]:
    """Keep a user-saved custom model visible in the dropdown."""
    values = list(choices)
    if current and current not in values:
        values.append(current)
    return [SelectOptionDict(value=value, label=value) for value in values]


async def _validate_api_key(
    session: aiohttp.ClientSession, api_key: str
) -> str | None:
    """Return an error key, or None if the key works."""
    try:
        async with session.get(
            TTS_MODELS_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status == 401:
                return "invalid_auth"
            if resp.status >= 400:
                return "cannot_connect"
    except aiohttp.ClientError:
        return "cannot_connect"
    except TimeoutError:
        return "cannot_connect"
    return None


class SonioxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Soniox."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Prompt for the API key."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_API_KEY][-8:])
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            error = await _validate_api_key(session, user_input[CONF_API_KEY])
            if error:
                errors["base"] = error
            else:
                return self.async_create_entry(title="Soniox", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Allow updating the API key on an existing entry."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            error = await _validate_api_key(session, user_input[CONF_API_KEY])
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(
                    entry, data={**entry.data, **user_input}
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return SonioxOptionsFlow()


class SonioxOptionsFlow(OptionsFlow):
    """Per-engine defaults that the user can change without re-adding the entry."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show / save the options form."""
        if user_input is not None:
            try:
                user_input[CONF_TTS_SAMPLE_RATE] = int(
                    user_input[CONF_TTS_SAMPLE_RATE]
                )
            except (KeyError, TypeError, ValueError):
                user_input[CONF_TTS_SAMPLE_RATE] = DEFAULT_TTS_SAMPLE_RATE
            return self.async_create_entry(title="", data=user_input)

        opts = self.config_entry.options
        lang_options = [
            SelectOptionDict(value=code, label=code) for code in SUPPORTED_LANGUAGES
        ]
        voice_options = [
            SelectOptionDict(value=v, label=v) for v in TTS_VOICES
        ]
        format_options = [
            SelectOptionDict(value=f, label=f) for f in TTS_AUDIO_FORMATS
        ]
        sample_rate_options = [
            SelectOptionDict(value=str(r), label=str(r)) for r in TTS_SAMPLE_RATES
        ]
        stt_model_options = _model_options(
            STT_REALTIME_MODELS, opts.get(CONF_STT_MODEL)
        )
        stt_async_model_options = _model_options(
            STT_ASYNC_MODELS, opts.get(CONF_STT_ASYNC_MODEL)
        )
        tts_model_options = _model_options(TTS_MODELS, opts.get(CONF_TTS_MODEL))

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_STT_MODEL,
                    default=opts.get(CONF_STT_MODEL, DEFAULT_STT_MODEL),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=stt_model_options, mode=SelectSelectorMode.DROPDOWN
                    )
                ),
                vol.Optional(
                    CONF_STT_ASYNC_MODEL,
                    default=opts.get(CONF_STT_ASYNC_MODEL, DEFAULT_STT_ASYNC_MODEL),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=stt_async_model_options,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_TTS_MODEL,
                    default=opts.get(CONF_TTS_MODEL, DEFAULT_TTS_MODEL),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=tts_model_options, mode=SelectSelectorMode.DROPDOWN
                    )
                ),
                vol.Optional(
                    CONF_TTS_VOICE,
                    default=opts.get(CONF_TTS_VOICE, DEFAULT_TTS_VOICE),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=voice_options, mode=SelectSelectorMode.DROPDOWN
                    )
                ),
                vol.Optional(
                    CONF_TTS_LANGUAGE,
                    default=opts.get(CONF_TTS_LANGUAGE, DEFAULT_TTS_LANGUAGE),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=lang_options, mode=SelectSelectorMode.DROPDOWN
                    )
                ),
                vol.Optional(
                    CONF_TTS_AUDIO_FORMAT,
                    default=opts.get(CONF_TTS_AUDIO_FORMAT, DEFAULT_TTS_AUDIO_FORMAT),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=format_options, mode=SelectSelectorMode.DROPDOWN
                    )
                ),
                vol.Optional(
                    CONF_TTS_SAMPLE_RATE,
                    default=str(
                        opts.get(CONF_TTS_SAMPLE_RATE, DEFAULT_TTS_SAMPLE_RATE)
                    ),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=sample_rate_options, mode=SelectSelectorMode.DROPDOWN
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
