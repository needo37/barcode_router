"""Config flow for Barcode Router."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import CONF_GROCY_API_KEY, CONF_GROCY_URL, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_GROCY_URL): str,
        vol.Required(CONF_GROCY_API_KEY): str,
    }
)


async def validate_grocy_connection(hass: HomeAssistant, url: str, api_key: str) -> None:
    """Validate Grocy connection."""
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"GROCY-API-KEY": api_key}
            async with session.get(
                f"{url.rstrip('/')}/api/system/info",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status != 200:
                    raise CannotConnect
    except aiohttp.ClientError as err:
        _LOGGER.exception("Error connecting to Grocy: %s", err)
        raise CannotConnect from err


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Barcode Router."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await validate_grocy_connection(
                    self.hass,
                    user_input[CONF_GROCY_URL],
                    user_input[CONF_GROCY_API_KEY],
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title="Barcode Router",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
