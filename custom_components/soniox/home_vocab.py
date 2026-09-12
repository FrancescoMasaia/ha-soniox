"""Collect spoken Home Assistant names for Soniox STT context."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
import re
from typing import Any

from homeassistant.const import EVENT_CORE_CONFIG_UPDATE
from homeassistant.core import Event, HomeAssistant, callback, split_entity_id
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
    floor_registry as fr,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

DATA_HOME_VOCAB = f"{DOMAIN}_home_vocab"

# Domains people actually speak to. Sensors are included only if exposed to Assist.
_VOICE_DOMAINS = {
    "alarm_control_panel",
    "climate",
    "cover",
    "fan",
    "humidifier",
    "input_boolean",
    "input_button",
    "light",
    "lock",
    "media_player",
    "person",
    "remote",
    "scene",
    "script",
    "siren",
    "switch",
    "todo",
    "vacuum",
    "valve",
    "water_heater",
    "weather",
    "zone",
}

# Single-token names that add noise without helping recognition.
_GENERIC_NAMES = {
    "battery",
    "binary sensor",
    "button",
    "energy",
    "humidity",
    "identify",
    "light",
    "motion",
    "power",
    "restart",
    "sensor",
    "signal",
    "status",
    "switch",
    "temperature",
    "update",
}

_ENTITY_ID_STYLE = re.compile(r"^[a-z][a-z0-9]+[._-][a-z0-9._-]+$")
_MAC_OR_HEX = re.compile(r"^[0-9a-f]{6,}$")


@dataclass(frozen=True)
class HomeVocab:
    """Spoken names discovered from the current Home Assistant house."""

    terms: list[str]
    home_name: str | None
    areas: list[str]
    floors: list[str]


class HomeVocabCache:
    """In-memory house vocabulary, rebuilt only when the house changes."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._vocab: HomeVocab | None = None
        self._unsubs: list[Callable[[], None]] = []
        self.users = 0

    def get(self) -> HomeVocab:
        """Return the cached vocab, collecting it once if needed."""
        if self._vocab is None:
            self._vocab = collect_home_vocab(self.hass)
        return self._vocab

    @callback
    def invalidate(self, *_args: Any) -> None:
        """Drop the snapshot so the next STT turn rebuilds it."""
        if self._vocab is not None:
            _LOGGER.debug("Soniox STT home vocab cache invalidated")
        self._vocab = None

    def async_setup(self) -> None:
        """Listen for house changes and warm the cache."""
        for event_type in (
            ar.EVENT_AREA_REGISTRY_UPDATED,
            dr.EVENT_DEVICE_REGISTRY_UPDATED,
            er.EVENT_ENTITY_REGISTRY_UPDATED,
            fr.EVENT_FLOOR_REGISTRY_UPDATED,
            EVENT_CORE_CONFIG_UPDATE,
        ):
            self._unsubs.append(
                self.hass.bus.async_listen(event_type, self._async_on_bus_event)
            )
        try:
            from homeassistant.components.homeassistant.exposed_entities import (
                async_listen_entity_updates,
            )

            self._unsubs.append(
                async_listen_entity_updates(self.hass, "conversation", self.invalidate)
            )
        except (HomeAssistantError, KeyError, AttributeError):
            pass
        self.get()

    @callback
    def _async_on_bus_event(self, _event: Event) -> None:
        self.invalidate()

    def async_unload(self) -> None:
        """Remove listeners and drop the snapshot."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        self._vocab = None


def async_setup_home_vocab_cache(hass: HomeAssistant) -> HomeVocabCache:
    """Create or reuse the house-wide cache for this Home Assistant instance."""
    cache = hass.data.get(DATA_HOME_VOCAB)
    if not isinstance(cache, HomeVocabCache):
        cache = HomeVocabCache(hass)
        cache.async_setup()
        hass.data[DATA_HOME_VOCAB] = cache
    cache.users += 1
    return cache


def async_unload_home_vocab_cache(hass: HomeAssistant) -> None:
    """Release one user of the cache; tear it down when unused."""
    cache = hass.data.get(DATA_HOME_VOCAB)
    if not isinstance(cache, HomeVocabCache):
        return
    cache.users -= 1
    if cache.users > 0:
        return
    cache.async_unload()
    hass.data.pop(DATA_HOME_VOCAB, None)


def get_cached_home_vocab(hass: HomeAssistant) -> HomeVocab:
    """Return cached house names, or collect once if setup has not run."""
    cache = hass.data.get(DATA_HOME_VOCAB)
    if isinstance(cache, HomeVocabCache):
        return cache.get()
    return collect_home_vocab(hass)


def collect_home_vocab(hass: HomeAssistant) -> HomeVocab:
    """Return area, floor, device, and entity names worth sending to Soniox."""
    seen: dict[str, str] = {}

    def add(name: str | None) -> None:
        cleaned = clean_term(name)
        if cleaned is None:
            return
        seen.setdefault(cleaned.casefold(), cleaned)

    home_name = clean_term(getattr(hass.config, "location_name", None))
    add(home_name)

    areas: list[str] = []
    for area in ar.async_get(hass).async_list_areas():
        add(area.name)
        if area.name:
            areas.append(area.name)
        for alias in area.aliases or ():
            add(alias)

    floors: list[str] = []
    floor_reg = fr.async_get(hass)
    for floor in floor_reg.async_list_floors():
        add(floor.name)
        if floor.name:
            floors.append(floor.name)
        for alias in floor.aliases or ():
            add(alias)

    expose_flags = _conversation_expose_flags(hass)
    entity_reg = er.async_get(hass)
    device_reg = dr.async_get(hass)
    used_devices: set[str] = set()

    for entity_id, entry in entity_reg.entities.items():
        if entry.disabled_by is not None:
            continue
        if not _include_entity(entity_id, entry, expose_flags):
            continue
        add(entry.name)
        add(entry.original_name)
        for alias in entry.aliases or ():
            add(alias)
        if state := hass.states.get(entity_id):
            add(state.attributes.get("friendly_name"))
        if entry.device_id and entry.device_id not in used_devices:
            used_devices.add(entry.device_id)
            device = device_reg.async_get(entry.device_id)
            if device is not None:
                add(device.name_by_user)
                add(device.name)

    # Zones and other voice entities that may have no registry entry.
    for state in hass.states.async_all():
        domain = split_entity_id(state.entity_id)[0]
        if domain not in _VOICE_DOMAINS:
            continue
        if state.entity_id in entity_reg.entities:
            continue
        add(state.attributes.get("friendly_name"))
        add(state.name)

    terms = list(seen.values())
    _LOGGER.debug("Soniox STT home vocab collected %s terms", len(terms))
    return HomeVocab(
        terms=terms,
        home_name=home_name,
        areas=areas,
        floors=floors,
    )


def _conversation_expose_flags(hass: HomeAssistant) -> dict[str, bool]:
    """Read Assist expose flags without writing new ones."""
    try:
        from homeassistant.components.homeassistant.exposed_entities import (
            async_get_assistant_settings,
        )

        settings = async_get_assistant_settings(hass, "conversation")
    except (HomeAssistantError, KeyError, AttributeError):
        return {}

    flags: dict[str, bool] = {}
    for entity_id, options in settings.items():
        if "should_expose" in options:
            flags[entity_id] = bool(options["should_expose"])
    return flags


def _include_entity(
    entity_id: str,
    entry: er.RegistryEntry,
    expose_flags: dict[str, bool],
) -> bool:
    exposed = expose_flags.get(entity_id)
    if exposed is False:
        return False
    if exposed is True:
        return True
    if entry.hidden_by is not None or entry.entity_category is not None:
        return False
    return split_entity_id(entity_id)[0] in _VOICE_DOMAINS


def clean_term(name: str | None) -> str | None:
    """Normalize a spoken name and drop values that will not help STT."""
    if not name or not isinstance(name, str):
        return None
    cleaned = " ".join(name.split()).strip(" -_|")
    if len(cleaned) < 2 or len(cleaned) > 80:
        return None
    folded = cleaned.casefold()
    if folded in _GENERIC_NAMES or folded.isdigit():
        return None
    if " " not in cleaned and _ENTITY_ID_STYLE.fullmatch(folded):
        return None
    compact = re.sub(r"[^a-z0-9]", "", folded)
    if _MAC_OR_HEX.fullmatch(compact) and len(compact) >= 8:
        return None
    return cleaned

