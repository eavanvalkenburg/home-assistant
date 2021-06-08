"""Config flow for Indego."""
from __future__ import annotations

import logging
from typing import Final

from pyIndego import IndegoAsyncClient
from requests.exceptions import ConnectTimeout, HTTPError
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

_LOGGER: Final = logging.getLogger(__name__)


def create_schema(user_input: ConfigType = None):
    """Create the schema with a default for username if existing input."""
    if user_input:
        return vol.Schema(
            {
                vol.Required(CONF_USERNAME, default=user_input[CONF_USERNAME]): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
    return vol.Schema(
        {
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
        }
    )


async def async_validate_input(data: ConfigType) -> None:
    """Validate the user input allows us to connect."""
    async with IndegoAsyncClient(
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
    ) as client:
        await client.login()


class IndegoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Canary."""

    VERSION = 1

    async def async_step_user(self, user_input: ConfigType | None = None) -> FlowResult:
        """Handle a flow initiated by the user."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=create_schema(user_input),
            )
        await self.async_set_unique_id(user_input[CONF_USERNAME])
        self._abort_if_unique_id_configured()
        try:
            await async_validate_input(user_input)
        except (ConnectTimeout, HTTPError):
            return self.async_show_form(
                step_id="user",
                data_schema=create_schema(user_input),
                errors={"base": "cannot_connect"},
            )
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception %s", exc)
            return self.async_abort(reason="unknown")
        return self.async_create_entry(
            title=user_input[CONF_USERNAME],
            data=user_input,
        )
