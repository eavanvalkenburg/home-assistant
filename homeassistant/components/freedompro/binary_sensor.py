"""Support for Freedompro binary_sensor."""
from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_MOTION,
    DEVICE_CLASS_OCCUPANCY,
    DEVICE_CLASS_OPENING,
    DEVICE_CLASS_SMOKE,
    BinarySensorEntity,
)
from homeassistant.const import CONF_API_KEY
from homeassistant.core import callback
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

DEVICE_CLASS_MAP = {
    "smokeSensor": DEVICE_CLASS_SMOKE,
    "occupancySensor": DEVICE_CLASS_OCCUPANCY,
    "motionSensor": DEVICE_CLASS_MOTION,
    "contactSensor": DEVICE_CLASS_OPENING,
}

DEVICE_KEY_MAP = {
    "smokeSensor": "smokeDetected",
    "occupancySensor": "occupancyDetected",
    "motionSensor": "motionDetected",
    "contactSensor": "contactSensorState",
}

SUPPORTED_SENSORS = {"smokeSensor", "occupancySensor", "motionSensor", "contactSensor"}


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Freedompro binary_sensor."""
    api_key = entry.data[CONF_API_KEY]
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        Device(hass, api_key, device, coordinator)
        for device in coordinator.data
        if device["type"] in SUPPORTED_SENSORS
    )


class Device(CoordinatorEntity, BinarySensorEntity):
    """Representation of an Freedompro binary_sensor."""

    def __init__(self, hass, api_key, device, coordinator):
        """Initialize the Freedompro binary_sensor."""
        super().__init__(coordinator)
        self._hass = hass
        self._session = aiohttp_client.async_get_clientsession(self._hass)
        self._api_key = api_key
        self._attr_name = device["name"]
        self._attr_unique_id = device["uid"]
        self._type = device["type"]
        self._characteristics = device["characteristics"]
        self._attr_device_info = {
            "name": self.name,
            "identifiers": {
                (DOMAIN, self.unique_id),
            },
            "model": self._type,
            "manufacturer": "Freedompro",
        }
        self._attr_device_class = DEVICE_CLASS_MAP[self._type]

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        device = next(
            (
                device
                for device in self.coordinator.data
                if device["uid"] == self.unique_id
            ),
            None,
        )
        if device is not None and "state" in device:
            state = device["state"]
            self._attr_is_on = state[DEVICE_KEY_MAP[self._type]]
        super()._handle_coordinator_update()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()
