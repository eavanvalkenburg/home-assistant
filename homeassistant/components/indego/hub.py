"""Bosch Indego Mower Hub."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

from aiohttp import ClientSession
from pyIndego import IndegoAsyncClient
from pyIndego.states import State

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STATE_LONGPOLL_TIMEOUT_REGULAR = 300
STATE_LONGPOLL_TIMEOUT_OPERATIONAL = 10


class IndegoHub:
    """Class for the IndegoHub."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, session: ClientSession
    ) -> None:
        """Initialize the IndegoHub."""
        self._hass: HomeAssistant = hass
        self._entry: ConfigEntry = entry
        self._username: str = entry.data[CONF_USERNAME]
        self._password: str = entry.data[CONF_PASSWORD]

        self._serial: str | None = None
        self._mower_name: str | None = None
        self._state_longpoll_timeout = STATE_LONGPOLL_TIMEOUT_REGULAR
        self._state_use_longpoll = True
        self.indego = IndegoAsyncClient(
            self._username,
            self._password,
            session=session,
        )
        self.duc_state: DataUpdateCoordinator | None = None
        self.duc_alerts: DataUpdateCoordinator | None = None
        self.duc_operating_data: DataUpdateCoordinator | None = None
        self.duc_generic: DataUpdateCoordinator | None = None
        self.duc_last_completed_mow: DataUpdateCoordinator | None = None
        self.duc_next_mow: DataUpdateCoordinator | None = None
        self.duc_updates_available: DataUpdateCoordinator | None = None
        self._latest_alert = None
        self._refresh_state_task: asyncio.Task | None = None

    async def async_setup_hub(self) -> None:
        """Login to the api."""
        login_success = await self.indego.login()
        if not login_success:
            raise AttributeError("Unable to login, please check your credentials")
        self._serial = self.indego.serial
        await self.indego.update_generic_data()
        await self.indego.update_location()
        await self.indego.update_calendar()
        if self.indego.generic_data.alm_name:
            self._mower_name = self.indego.generic_data.alm_name
        else:
            self._mower_name = self._serial

        device_registry = await dr.async_get_registry(self._hass)
        device_registry.async_get_or_create(
            config_entry_id=self._entry.entry_id,
            identifiers={(DOMAIN, self.serial)},
            connections={(DOMAIN, self.serial)},
            name=f"Bosch Indego Mower - {self.mower_name}",
            manufacturer="Bosch",
            model=self.indego.generic_data.model_description,
            sw_version=self.indego.generic_data.alm_firmware_version,
            suggested_area="garden",
        )

        self.duc_state = DataUpdateCoordinator(
            self._hass,
            _LOGGER,
            name=f"{DOMAIN}_{self._serial}_state",
            update_interval=None,  # timedelta(seconds=1),
            update_method=self.refresh_state,
        )
        self.duc_operating_data = DataUpdateCoordinator(
            self._hass,
            _LOGGER,
            name=f"{DOMAIN}_{self._serial}_operating_data",
            update_interval=None,
            update_method=self.indego.get_operating_data,
        )
        self.duc_generic = DataUpdateCoordinator(
            self._hass,
            _LOGGER,
            name=f"{DOMAIN}_{self._serial}_generic",
            update_interval=timedelta(minutes=10),
            update_method=self.indego.get_generic_data,
        )
        self.duc_last_completed_mow = DataUpdateCoordinator(
            self._hass,
            _LOGGER,
            name=f"{DOMAIN}_{self._serial}_last_completed_mow",
            update_interval=timedelta(hours=1),
            update_method=self.indego.get_last_completed_mow,
        )
        self.duc_next_mow = DataUpdateCoordinator(
            self._hass,
            _LOGGER,
            name=f"{DOMAIN}_{self._serial}_next_mow",
            update_interval=timedelta(hours=1),
            update_method=self.indego.get_next_mow,
        )
        self.duc_alerts = DataUpdateCoordinator(
            self._hass,
            _LOGGER,
            name=f"{DOMAIN}_{self._serial}_alerts",
            update_interval=timedelta(minutes=10),
            update_method=self.indego.get_alerts,
        )
        self.duc_updates_available = DataUpdateCoordinator(
            self._hass,
            _LOGGER,
            name=f"{DOMAIN}_{self._serial}_updates_available",
            update_interval=timedelta(hours=24),
            update_method=self.indego.get_updates_available,
        )
        self.duc_state.async_add_listener(self._handle_update_state)
        self._entry.async_on_unload(
            self._hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STOP, self.async_shutdown
            )
        )

    async def async_group_first_refresh(self, _) -> None:
        """Refresh data for the first time when a config entry is setup.

        Will automatically raise ConfigEntryNotReady if the refresh
        fails. Additionally logging is handled by config entry setup
        to ensure that multiple retries do not cause log spam.
        """
        assert self.duc_alerts
        assert self.duc_generic
        assert self.duc_last_completed_mow
        assert self.duc_next_mow
        assert self.duc_operating_data
        assert self.duc_updates_available
        assert self.duc_state
        results = await asyncio.gather(
            *[
                self.duc_alerts.async_config_entry_first_refresh(),
                self.duc_generic.async_config_entry_first_refresh(),
                self.duc_last_completed_mow.async_config_entry_first_refresh(),
                self.duc_next_mow.async_config_entry_first_refresh(),
                self.duc_operating_data.async_config_entry_first_refresh(),
                self.duc_updates_available.async_config_entry_first_refresh(),
                self.indego.update_state(longpoll=False),
            ],
            return_exceptions=True,
        )
        for item in results:
            if isinstance(item, Exception):
                raise item
        self.duc_state.async_set_updated_data(
            {
                "state": self.indego.state,
                "state_description": self.indego.state_description,
                "state_description_detail": self.indego.state_description_detail,
            }
        )

    async def async_shutdown(self, *_) -> None:
        """Remove all future updates, cancel tasks and close the client."""
        if self._refresh_state_task:
            self._refresh_state_task.cancel()
            await self._refresh_state_task

    @callback
    def _handle_update_state(self):
        """Call update state after it has finished."""
        _LOGGER.debug("Callback of state update")
        assert self.duc_state
        state = self.duc_state.data["state"]
        if state:
            _LOGGER.debug("New state of indego: %s", state)
            state_id = state.state
            if (500 <= state_id <= 799) or (state_id in (257, 260)):
                _LOGGER.debug("Requesting operating data update")
                assert self.duc_operating_data
                self._hass.create_task(self.duc_operating_data.async_request_refresh())
                self._state_longpoll_timeout = STATE_LONGPOLL_TIMEOUT_OPERATIONAL
                # self._state_use_longpoll = False
            else:
                # self._state_use_longpoll = True
                self._state_longpoll_timeout = STATE_LONGPOLL_TIMEOUT_REGULAR
            if state.error != self._latest_alert:
                self._latest_alert = state.error
                assert self.duc_alerts
                self._hass.create_task(self.duc_alerts.async_request_refresh())
        self._hass.create_task(self.duc_state.async_request_refresh())

    async def refresh_state(self) -> dict[str, State | str | None]:
        """Update the state, if necessary update operating data and recall itself."""
        _LOGGER.debug("Starting state update")
        # TODO: check cancelling when shutting down
        self._refresh_state_task = self._hass.async_create_task(
            self.indego.update_state(
                longpoll=self._state_use_longpoll,
                longpoll_timeout=self._state_longpoll_timeout,
            )
        )
        await self._refresh_state_task
        return {
            "state": self.indego.state,
            "state_description": self.indego.state_description,
            "state_description_detail": self.indego.state_description_detail,
        }

    async def download_map(self, filename: str):
        """Download the map of the lawn."""
        _LOGGER.debug("Downloading map to %s", filename)
        await self.indego.download_map(filename)

    @property
    def serial(self) -> str:
        """Return the serial of the mower."""
        assert self._serial
        return self._serial

    @property
    def mower_name(self) -> str:
        """Return the mower_name of the mower."""
        assert self._mower_name
        return self._mower_name
