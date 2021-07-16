"""Bosch Indego Mower integration."""
from __future__ import annotations

import logging
from pathlib import Path

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_START
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

# from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_DOWNLAD_MAP,
    CONF_SEND_COMMAND,
    CONF_SMARTMOWING,
    DEFAULT_MAP_NAME,
    DEFAULT_NAME_COMMANDS,
    DOMAIN,
    PLATFORMS,
    SERVICE_NAME_COMMAND,
    SERVICE_NAME_DOWNLOAD_MAP,
    SERVICE_NAME_SMARTMOW,
)
from .hub import IndegoHub

_LOGGER = logging.getLogger(__name__)

SERVICE_SCHEMA_COMMAND = vol.Schema({vol.Required(CONF_SEND_COMMAND): cv.string})

SERVICE_SCHEMA_SMARTMOWING = vol.Schema({vol.Required(CONF_SMARTMOWING): cv.string})

SERVICE_SCHEMA_DOWNLOAD_MAP = vol.Schema(
    {vol.Optional(CONF_DOWNLAD_MAP, default=DEFAULT_MAP_NAME): cv.string}
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Indego from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    cs = async_get_clientsession(hass)
    # cs._timeout = 600
    hub = hass.data[DOMAIN][entry.entry_id] = IndegoHub(hass, entry, cs)
    await hub.async_setup_hub()
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    async def async_send_command(call):
        """Handle the service call."""
        name = call.data.get(CONF_SEND_COMMAND, DEFAULT_NAME_COMMANDS)
        await hass.data[DOMAIN][entry.entry_id].indego.put_command(name)
        await hass.data[DOMAIN][entry.entry_id].duc_state.async_request_refresh()

    async def async_send_smartmowing(call):
        """Handle the service call."""
        name = call.data.get(CONF_SMARTMOWING, DEFAULT_NAME_COMMANDS)
        await hass.data[DOMAIN][entry.entry_id].indego.put_mow_mode(name)
        await hass.data[DOMAIN][entry.entry_id].duc_generic.async_request_refresh()

    Path(hass.config.path("www")).mkdir(exist_ok=True)

    async def async_download_map(call):
        name = call.data.get(CONF_DOWNLAD_MAP, DEFAULT_MAP_NAME)
        _LOGGER.debug("Indego.download_map service called")
        await hass.data[DOMAIN][entry.entry_id].download_map(
            hass.config.path(f"www/{name}.svg")
        )

    hass.services.async_register(
        DOMAIN, SERVICE_NAME_COMMAND, async_send_command, SERVICE_SCHEMA_COMMAND
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_NAME_SMARTMOW,
        async_send_smartmowing,
        SERVICE_SCHEMA_SMARTMOWING,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_NAME_DOWNLOAD_MAP,
        async_download_map,
        SERVICE_SCHEMA_DOWNLOAD_MAP,
    )
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, hub.async_group_first_refresh)
    # hass.async_create_task(hub.async_group_first_refresh)
    # hass.async_add_job(hub.async_group_first_refresh)
    # await hub.async_group_first_refresh()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hub: IndegoHub = hass.data[DOMAIN].pop(entry.entry_id)
        await hub.async_shutdown()
    return unload_ok
