"""Class for Indego Sensors."""
from __future__ import annotations

from abc import abstractmethod
import logging

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
    ATTR_MAP_UPDATE_AVAILABLE,
    ATTR_STATE_ID,
    ATTR_SVG_X_POS,
    ATTR_SVG_Y_POS,
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
        self._hub: IndegoHub = hub
        self._attr_state: StateType = None

    @property
    def _serial(self) -> str:
        """Return the serial of the mower."""
        return self._hub.serial

    @property
    def _mower_name(self) -> str:
        """Return the mower name of the mower."""
        return self._hub.mower_name

    @abstractmethod
    def async_handle_state_update(self) -> None:
        """Abstract method to be implemented by the subclasses."""

    async def async_added_to_hass(self) -> None:
        """Once the sensor is added, see if it was there before and pull in that state."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state is not None and state.state is not None:
            self._attr_state = state.state
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_handle_state_update)
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device_info."""
        return {
            "connections": {(DOMAIN, self._serial)},
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
    def async_handle_state_update(self) -> None:
        """Handle the state update of the coordinator."""
        self._attr_state = self.coordinator.data["state_description"]
        self._attr_extra_state_attributes = {
            ATTR_STATE_ID: self.coordinator.data["state"].state
        }
        self.async_write_ha_state()


class IndegoMowerStateDetail(IndegoBaseSensor):
    """Mower state detail sensor."""

    def __init__(self, entry, hub) -> None:
        """Initialize Mower State Detail Sensor."""
        super().__init__(coordinator=hub.duc_state, entry=entry, hub=hub)
        self._attr_name = f"{self._mower_name} Mower State Detail"
        self._attr_unique_id = f"{self._serial}_mower_state_detail"
        self._attr_icon = "mdi:robot-mower-outline"

    @callback
    def async_handle_state_update(self) -> None:
        """Handle the state update of the coordinator."""
        self._attr_state = self.coordinator.data["state_description_detail"]
        self._attr_extra_state_attributes = {
            ATTR_STATE_ID: self.coordinator.data["state"].state
        }
        self.async_write_ha_state()


class IndegoBattery(IndegoBaseSensor):
    """Battery sensor."""

    def __init__(self, entry, hub) -> None:
        """Initialize Mower State Detail Sensor."""
        super().__init__(coordinator=hub.duc_operating_data, entry=entry, hub=hub)
        self._attr_device_class = DEVICE_CLASS_BATTERY
        self._attr_unit_of_measurement = "%"
        self._attr_name = f"{self._mower_name} Battery %"
        self._attr_unique_id = f"{self._serial}_battery"
        self._attr_icon = "mdi:battery"

    @callback
    def async_handle_state_update(self) -> None:
        """Handle the state update of the coordinator."""
        battery: Battery = self.coordinator.data.battery
        self._attr_state = battery.percent_adjusted
        assert isinstance(self._attr_state, int)
        self._attr_icon = icon_for_battery_level(
            self._attr_state,
            self._hub.indego.state.state in (257, 260),
        )
        # TODO: check unit of temps
        self._attr_extra_state_attributes = {
            ATTR_VOLTAGE: battery.voltage,
            ATTR_DISCHARGE: battery.discharge,
            ATTR_CYCLES: battery.cycles,
            ATTR_BATTERY_TEMP: battery.battery_temp,
            ATTR_AMBIENT_TEMP: battery.ambient_temp,
        }
        self.async_write_ha_state()


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
    def async_handle_state_update(self) -> None:
        """Handle the state update of the coordinator."""
        state: State = self.coordinator.data["state"]
        self._attr_state = state.mowed
        self._attr_extra_state_attributes = {
            ATTR_LAST_SESSION_OPERATION_MIN: state.runtime.session.operate,
            ATTR_LAST_SESSION_CUT_MIN: state.runtime.session.cut,
            ATTR_LAST_SESSION_CHARGE_MIN: state.runtime.session.charge,
        }
        self.async_write_ha_state()


class IndegoLastCompleted(IndegoBaseSensor):
    """Last Completed sensor."""

    def __init__(self, entry, hub) -> None:
        """Initialize Last Completed Sensor."""
        super().__init__(coordinator=hub.duc_last_completed_mow, entry=entry, hub=hub)
        self._attr_name = f"{self._mower_name} Last Completed"
        self._attr_unique_id = f"{self._serial}_last_completed"
        self._attr_icon = "mdi:calendar-check"
        self._attr_device_class = DEVICE_CLASS_TIMESTAMP
        self._attr_unit_of_measurement = "ISO8601"

    @callback
    def async_handle_state_update(self) -> None:
        """Handle the state update of the coordinator."""
        self._attr_state = self.coordinator.data.isoformat()
        self.async_write_ha_state()


class IndegoNextMow(IndegoBaseSensor):
    """Last Completed sensor."""

    def __init__(self, entry, hub) -> None:
        """Initialize Last Completed Sensor."""
        super().__init__(coordinator=hub.duc_next_mow, entry=entry, hub=hub)
        self._attr_name = f"{self._mower_name} Next Mow"
        self._attr_unique_id = f"{self._serial}_next_mow"
        self._attr_icon = "mdi:calendar-clock"
        self._attr_device_class = DEVICE_CLASS_TIMESTAMP
        self._attr_unit_of_measurement = "ISO8601"

    @callback
    def async_handle_state_update(self) -> None:
        """Handle the state update of the coordinator."""
        self._attr_state = self.coordinator.data.isoformat()
        self.async_write_ha_state()


class IndegoMowingMode(IndegoBaseSensor):
    """Mowing Mode sensor."""

    def __init__(self, entry, hub) -> None:
        """Initialize Mowing Mode Sensor."""
        super().__init__(coordinator=hub.duc_generic, entry=entry, hub=hub)
        self._attr_name = f"{self._mower_name} Mowing Mode"
        self._attr_unique_id = f"{self._serial}_mowing_mode"
        self._attr_icon = "mdi:alpha-m-circle-outline"

    @callback
    def async_handle_state_update(self) -> None:
        """Handle the state update of the coordinator."""
        self._attr_state = self.coordinator.data.mowing_mode_description
        self.async_write_ha_state()


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
    def async_handle_state_update(self) -> None:
        """Handle the state update of the coordinator."""
        state: State = self.coordinator.data["state"]
        self._attr_state = state.runtime.total.cut
        self._attr_extra_state_attributes = {
            ATTR_TOTAL_OPERATION_TIME: state.runtime.total.operate,
            ATTR_TOTAL_CHARGING_TIME: state.runtime.total.charge,
        }
        self.async_write_ha_state()


class IndegoXPosition(IndegoBaseSensor):
    """X position sensor."""

    def __init__(self, entry, hub) -> None:
        """Initialize X position Sensor."""
        super().__init__(coordinator=hub.duc_state, entry=entry, hub=hub)
        self._attr_name = f"{self._mower_name} X Position"
        self._attr_unique_id = f"{self._serial}_x_position"
        self._attr_icon = "mdi:crosshairs-gps"

    @callback
    def async_handle_state_update(self) -> None:
        """Handle the state update of the coordinator."""
        self._attr_state = self.coordinator.data["state"].xPos
        self._attr_extra_state_attributes = {
            ATTR_MAP_UPDATE_AVAILABLE: self.coordinator.data[
                "state"
            ].map_update_available,
            ATTR_SVG_X_POS: self.coordinator.data["state"].svg_xPos,
        }
        self.async_write_ha_state()


class IndegoYPosition(IndegoBaseSensor):
    """Y position sensor."""

    def __init__(self, entry, hub) -> None:
        """Initialize Y position Sensor."""
        super().__init__(coordinator=hub.duc_state, entry=entry, hub=hub)
        self._attr_name = f"{self._mower_name} Y Position"
        self._attr_unique_id = f"{self._serial}_y_position"
        self._attr_icon = "mdi:crosshairs-gps"

    @callback
    def async_handle_state_update(self) -> None:
        """Handle the state update of the coordinator."""
        self._attr_state = self.coordinator.data["state"].yPos
        self._attr_extra_state_attributes = {
            ATTR_MAP_UPDATE_AVAILABLE: self.coordinator.data[
                "state"
            ].map_update_available,
            ATTR_SVG_Y_POS: self.coordinator.data["state"].svg_yPos,
        }
        self.async_write_ha_state()
