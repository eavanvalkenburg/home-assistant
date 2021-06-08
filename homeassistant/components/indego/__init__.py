"""Bosch Indego Mower integration."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_SEND_COMMAND,
    ATTR_SMARTMOWING,
    DEFAULT_NAME_COMMANDS,
    DOMAIN,
    PLATFORMS,
    SERVICE_NAME_COMMAND,
    SERVICE_NAME_SMARTMOW,
)
from .hub import IndegoHub

_LOGGER = logging.getLogger(__name__)

SERVICE_SCHEMA_COMMAND = vol.Schema({vol.Required(ATTR_SEND_COMMAND): cv.string})

SERVICE_SCHEMA_SMARTMOWING = vol.Schema({vol.Required(ATTR_SMARTMOWING): cv.string})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Indego from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hub = hass.data[DOMAIN][entry.entry_id] = IndegoHub(hass, entry)
    await hub.async_setup_hub()
    await hub.async_group_first_refresh()

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    async def async_send_command(call):
        """Handle the service call."""
        name = call.data.get(ATTR_SEND_COMMAND, DEFAULT_NAME_COMMANDS)
        await hass.data[DOMAIN][entry.entry_id].indego.put_command(name)
        await hass.data[DOMAIN][entry.entry_id].duc_state.async_request_refresh()

    async def async_send_smartmowing(call):
        """Handle the service call."""
        name = call.data.get(ATTR_SMARTMOWING, DEFAULT_NAME_COMMANDS)
        await hass.data[DOMAIN][entry.entry_id].indego.put_mow_mode(name)
        await hass.data[DOMAIN][entry.entry_id].duc_generic.async_request_refresh()

    hass.services.async_register(
        DOMAIN, SERVICE_NAME_COMMAND, async_send_command, SERVICE_SCHEMA_COMMAND
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_NAME_SMARTMOW,
        async_send_smartmowing,
        SERVICE_SCHEMA_SMARTMOWING,
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hub: IndegoHub = hass.data[DOMAIN].pop(entry.entry_id)
        await hub.async_shutdown()
    return unload_ok
