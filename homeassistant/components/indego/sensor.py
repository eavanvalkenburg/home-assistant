"""Class for Indego Sensors."""
from __future__ import annotations

from abc import abstractmethod
import logging
from typing import Any

from pyIndego.states import Battery, State

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_VOLTAGE,
    DEVICE_CLASS_BATTERY,
    DEVICE_CLASS_TIMESTAMP,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.icon import icon_for_battery_level
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    ATTR_AMBIENT_TEMP,
    ATTR_BATTERY_TEMP,
    ATTR_CYCLES,
    ATTR_DISCHARGE,
    ATTR_LAST_SESSION_CHARGE_MIN,
    ATTR_LAST_SESSION_CUT_MIN,
    ATTR_LAST_SESSION_OPERATION_MIN,
    ATTR_STATE_NUMBER,
    ATTR_TOTAL_CHARGING_TIME,
    ATTR_TOTAL_OPERATION_TIME,
    DOMAIN,
)
from .hub import IndegoHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Indego sensors from a config entry."""
    hub: IndegoHub = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            IndegoBattery(entry, hub),
            IndegoLastCompleted(entry, hub),
            IndegoLawnMowed(entry, hub),
            IndegoMowerState(entry, hub),
            IndegoMowerStateDetail(entry, hub),
            IndegoMowingMode(entry, hub),
            IndegoMowtimeTotal(entry, hub),
            IndegoNextMow(entry, hub),
            IndegoXPosition(entry, hub),
            IndegoYPosition(entry, hub),
        ]
    )


class IndegoBaseSensor(RestoreEntity, CoordinatorEntity):
    """Class for Indego Sensors."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, entry: ConfigEntry, hub: IndegoHub
    ) -> None:
        """Initialize a Base Indego sensor."""
        super().__init__(coordinator)
        _LOGGER.warning(
            "Coordinator is %s, with type %s", self.coordinator, type(self.coordinator)
        )
        assert hub._serial
        self._serial: str = hub._serial
        if hub._mower_name:
            self._mower_name: str = hub._mower_name
        else:
            self._mower_name: str = hub._serial
        self._hub: IndegoHub = hub
        self._attr_state: StateType = None
        self.coordinator: Any = None

    @abstractmethod
    def async_handle_state_update(self):
        """Abstract method to be implemented by the subclasses."""

    async def async_added_to_hass(self) -> None:
        """Once the sensor is added, see if it was there before and pull in that state."""
        await super().async_added_to_hass()
        _LOGGER.warning(
            "Coordinator is %s, with type %s", self.coordinator, type(self.coordinator)
        )
        state = await self.async_get_last_state()
        if state is not None and state.state is not None:
            self._attr_state = state.state
        if self.coordinator is not None:
            self.async_on_remove(
                self.coordinator.async_add_listener(self.async_handle_state_update)
            )

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device_info."""
        assert self.name is not None
        return {
            "name": self.name,
            "identifiers": {(DOMAIN, self._serial)},
            "manufacturer": "Bosch",
            "suggested_area": "garden",
            "model": self._hub.indego.generic_data.model_description,
            "sw_version": self._hub.indego.generic_data.alm_firmware_version,
            "via_device": (DOMAIN, self._serial),
        }


class IndegoMowerState(IndegoBaseSensor):
    """Mower state sensor."""

    def __init__(self, entry, hub) -> None:
        """Initialize Mower State Sensor."""
        super().__init__(coordinator=hub.duc_state, entry=entry, hub=hub)
        self._attr_name = f"{self._mower_name} Mower State"
        self._attr_unique_id = f"{self._serial}_mower_state"
        self._attr_icon = "mdi:robot-mower-outline"

    @callback
    def async_handle_state_update(self):
        """Handle the state update of the coordinator."""
        self._attr_state = self.coordinator.data["state"]


class IndegoMowerStateDetail(IndegoBaseSensor):
    """Mower state detail sensor."""

    def __init__(self, entry, hub) -> None:
        """Initialize Mower State Detail Sensor."""
        super().__init__(coordinator=hub.duc_state, entry=entry, hub=hub)
        self._attr_name = f"{self._mower_name} Mower State Detail"
        self._attr_unique_id = f"{self._serial}_mower_state_detail"
        self._attr_icon = "mdi:robot-mower-outline"

    @callback
    def async_handle_state_update(self):
        """Handle the state update of the coordinator."""
        self._attr_state = self.coordinator.data["state_description_detail"]
        self._attr_extra_state_attributes = {
            ATTR_STATE_NUMBER: self.coordinator.data["state"].state
        }


class IndegoBattery(IndegoBaseSensor):
    """Battery sensor."""

    def __init__(self, entry, hub) -> None:
        """Initialize Mower State Detail Sensor."""
        super().__init__(coordinator=hub.duc_operating_data, entry=entry, hub=hub)
        self._attr_device_class = DEVICE_CLASS_BATTERY
        self._attr_unit_of_measurement = "%"
        self._attr_name = f"{self._mower_name} battery %"
        self._attr_unique_id = f"{self._serial}_battery"
        self._attr_icon = "mdi:battery"

    @callback
    def async_handle_state_update(self):
        """Handle the state update of the coordinator."""
        battery: Battery = self.coordinator.data.battery
        self._attr_state = battery.percent_adjusted
        self._attr_icon = icon_for_battery_level(
            self._attr_state,
            self._hub.indego.state_description_detail == "Charging",
        )
        # TODO: check unit of temps
        self._attr_extra_state_attributes = {
            ATTR_VOLTAGE: battery.voltage,
            ATTR_DISCHARGE: battery.discharge,
            ATTR_CYCLES: battery.cycles,
            ATTR_BATTERY_TEMP: battery.battery_temp,
            ATTR_AMBIENT_TEMP: battery.ambient_temp,
        }


class IndegoLawnMowed(IndegoBaseSensor):
    """Lawn mowed sensor."""

    def __init__(self, entry, hub) -> None:
        """Initialize Lawn Mowed Sensor."""
        super().__init__(coordinator=hub.duc_state, entry=entry, hub=hub)
        self._attr_name = f"{self._mower_name} Lawn Mowed"
        self._attr_unique_id = f"{self._serial}_lawn_mowed"
        self._attr_icon = "mdi:grass"
        self._attr_unit_of_measurement = "%"

    @callback
    def async_handle_state_update(self):
        """Handle the state update of the coordinator."""
        state: State = self.coordinator.data["state"]
        self._attr_state = state.mowed
        self._attr_extra_state_attributes = {
            ATTR_LAST_SESSION_OPERATION_MIN: state.runtime.session.operate,
            ATTR_LAST_SESSION_CUT_MIN: state.runtime.session.cut,
            ATTR_LAST_SESSION_CHARGE_MIN: state.runtime.session.charge,
        }


class IndegoLastCompleted(IndegoBaseSensor):
    """Last Completed sensor."""

    def __init__(self, entry, hub) -> None:
        """Initialize Last Completed Sensor."""
        super().__init__(coordinator=hub.duc_generic, entry=entry, hub=hub)
        self._attr_name = f"{self._mower_name} Last Completed"
        self._attr_unique_id = f"{self._serial}_last_completed"
        self._attr_icon = "mdi:calendar-check"
        self._attr_device_class = DEVICE_CLASS_TIMESTAMP
        self._attr_unit_of_measurement = "ISO8601"

    @callback
    def async_handle_state_update(self):
        """Handle the state update of the coordinator."""
        self._attr_state = self.coordinator.data["last_completed_mow"].isoformat()


class IndegoNextMow(IndegoBaseSensor):
    """Last Completed sensor."""

    def __init__(self, entry, hub) -> None:
        """Initialize Last Completed Sensor."""
        super().__init__(coordinator=hub.duc_generic, entry=entry, hub=hub)
        self._attr_name = f"{self._mower_name} Next Mow"
        self._attr_unique_id = f"{self._serial}_next_mow"
        self._attr_icon = "mdi:calendar-clock"
        self._attr_device_class = DEVICE_CLASS_TIMESTAMP
        self._attr_unit_of_measurement = "ISO8601"

    @callback
    def async_handle_state_update(self):
        """Handle the state update of the coordinator."""
        self._attr_state = self.coordinator.data["next_mow"].isoformat()


class IndegoMowingMode(IndegoBaseSensor):
    """Mowing Mode sensor."""

    def __init__(self, entry, hub) -> None:
        """Initialize Mowing Mode Sensor."""
        super().__init__(coordinator=hub.duc_generic, entry=entry, hub=hub)
        self._attr_name = f"{self._mower_name} Mowing Mode"
        self._attr_unique_id = f"{self._serial}_mowing_mode"
        self._attr_icon = "mdi:alpha-m-circle-outline"

    @callback
    def async_handle_state_update(self):
        """Handle the state update of the coordinator."""
        self._attr_state = self.coordinator.data["generic_data"].mowing_mode_description


class IndegoMowtimeTotal(IndegoBaseSensor):
    """Runtime sensor."""

    def __init__(self, entry, hub) -> None:
        """Initialize Runtime Sensor."""
        super().__init__(coordinator=hub.duc_state, entry=entry, hub=hub)
        self._attr_name = f"{self._mower_name} Mowing Total"
        self._attr_unique_id = f"{self._serial}_mowing_total"
        self._attr_icon = "mdi:information-outline"
        self._attr_unit_of_measurement = "h"

    @callback
    def async_handle_state_update(self):
        """Handle the state update of the coordinator."""
        state: State = self.coordinator.data["state"]
        self._attr_state = state.runtime.total.cut
        self._attr_extra_state_attributes = {
            ATTR_TOTAL_OPERATION_TIME: state.runtime.total.operate,
            ATTR_TOTAL_CHARGING_TIME: state.runtime.total.charge,
        }


class IndegoXPosition(IndegoBaseSensor):
    """X position sensor."""

    def __init__(self, entry, hub) -> None:
        """Initialize X position Sensor."""
        super().__init__(coordinator=hub.duc_state, entry=entry, hub=hub)
        self._attr_name = f"{self._mower_name} X Position"
        self._attr_unique_id = f"{self._serial}_x_position"
        self._attr_icon = "mdi:crosshairs-gps"

    @callback
    def async_handle_state_update(self):
        """Handle the state update of the coordinator."""
        self._attr_state = self.coordinator.data["state"].xPos


class IndegoYPosition(IndegoBaseSensor):
    """Y position sensor."""

    def __init__(self, entry, hub) -> None:
        """Initialize Y position Sensor."""
        super().__init__(coordinator=hub.duc_state, entry=entry, hub=hub)
        self._attr_name = f"{self._mower_name} Y Position"
        self._attr_unique_id = f"{self._serial}_y_position"
        self._attr_icon = "mdi:crosshairs-gps"

    @callback
    def async_handle_state_update(self):
        """Handle the state update of the coordinator."""
        self._attr_state = self.coordinator.data["state"].yPos
