"""Bosch Indego Mower Hub."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging

from pyIndego import IndegoAsyncClient
from pyIndego.states import Alert, GenericData, OperatingData, State

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class IndegoHub:
    """Class for the IndegoHub."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the IndegoHub."""
        self._hass: HomeAssistant = hass
        self._username: str = entry.data[CONF_USERNAME]
        self._password: str = entry.data[CONF_PASSWORD]

        self._serial: str | None = None
        self._mower_name: str | None = None
        self.indego: IndegoAsyncClient = IndegoAsyncClient(
            self._username, self._password
        )
        self.duc_state: DataUpdateCoordinator | None = None
        self.duc_alerts: DataUpdateCoordinator | None = None
        self.duc_operating_data: DataUpdateCoordinator | None = None
        self.duc_generic: DataUpdateCoordinator | None = None
        self.duc_updates_available: DataUpdateCoordinator | None = None
        self._latest_alert = None

    async def async_setup_hub(self) -> None:
        """Login to the api."""
        login_success = await self.indego.login()
        if not login_success:
            raise AttributeError("Unable to login, please check your credentials")
        self._serial = self.indego.serial
        await self.indego.update_generic_data()
        self._mower_name = self.indego.generic_data.alm_name

        self.duc_state = DataUpdateCoordinator(
            self._hass,
            _LOGGER,
            name=f"{DOMAIN}_{self._serial}_state",
            update_interval=timedelta(seconds=1),
            update_method=self.refresh_state,
        )
        self.duc_operating_data = DataUpdateCoordinator(
            self._hass,
            _LOGGER,
            name=f"{DOMAIN}_{self._serial}_operating_data",
            update_interval=None,
            update_method=self.refresh_operating_data,
        )
        self.duc_generic = DataUpdateCoordinator(
            self._hass,
            _LOGGER,
            name=f"{DOMAIN}_{self._serial}_generic",
            update_interval=timedelta(minutes=10),
            update_method=self.refresh_generic_data,
        )
        self.duc_alerts = DataUpdateCoordinator(
            self._hass,
            _LOGGER,
            name=f"{DOMAIN}_{self._serial}_alerts",
            update_interval=timedelta(minutes=10),
            update_method=self.refresh_alerts,
        )
        self.duc_updates_available = DataUpdateCoordinator(
            self._hass,
            _LOGGER,
            name=f"{DOMAIN}_{self._serial}_updates_available",
            update_interval=timedelta(hours=24),
            update_method=self.refresh_updates_available,
        )
        self._hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self.async_shutdown)

    async def async_group_first_refresh(self) -> None:
        """Refresh data for the first time when a config entry is setup.

        Will automatically raise ConfigEntryNotReady if the refresh
        fails. Additionally logging is handled by config entry setup
        to ensure that multiple retries do not cause log spam.
        """
        assert self.duc_alerts
        assert self.duc_generic
        assert self.duc_operating_data
        assert self.duc_state
        assert self.duc_updates_available
        not_ready = await asyncio.gather(
            *[
                self.duc_alerts.async_config_entry_first_refresh(),
                self.duc_generic.async_config_entry_first_refresh(),
                self.duc_operating_data.async_config_entry_first_refresh(),
                self.duc_state.async_config_entry_first_refresh(),
                self.duc_updates_available.async_config_entry_first_refresh(),
            ],
            return_exceptions=True,
        )
        for item in not_ready:
            if isinstance(item, Exception):
                raise item

    async def async_shutdown(self, *_) -> None:
        """Remove all future updates, cancel tasks and close the client."""
        await self.indego.close()

    async def refresh_state(self) -> dict[str, State | str | None]:
        """Update the state, if necessary update operating data and recall itself."""
        await self.indego.update_state(longpoll=True, longpoll_timeout=300)
        if self.indego.state:
            state = self.indego.state.state
            if (500 <= state <= 799) or (state in (257, 260)):
                assert self.duc_operating_data
                await self.duc_operating_data.async_request_refresh()
            if self.indego.state.error != self._latest_alert:
                self._latest_alert = self.indego.state.error
                assert self.duc_alerts
                await self.duc_alerts.async_request_refresh()
        # TODO: check recall of update_state
        # self.refresh_state_task = await self.duc_state.async_refresh()
        return {
            "state": self.indego.state,
            "state_description_detail": self.indego.state_description_detail,
        }

    async def refresh_generic_data(self) -> dict[str, GenericData | datetime | None]:
        """Refresh Indego generic data."""
        results = await asyncio.gather(
            *[
                self.indego.update_generic_data(),
                self.indego.update_last_completed_mow(),
                self.indego.update_next_mow(),
            ],
            return_exceptions=True,
        )
        for res in results:
            if res:
                raise res
        return {
            "generic": self.indego.generic_data,
            "last_completed_mow": self.indego.last_completed_mow,
            "next_mow": self.indego.next_mow,
        }

    async def refresh_operating_data(self) -> OperatingData:
        """Refresh Indego operating data."""
        await self.indego.update_operating_data()
        return self.indego.operating_data

    async def refresh_alerts(self) -> list[Alert] | None:
        """Refresh Indego alerts."""
        await self.indego.update_alerts()
        return self.indego.alerts

    async def refresh_updates_available(self) -> bool:
        """Refresh Indego updates available."""
        await self.indego.update_updates_available()
        return self.indego.update_available
