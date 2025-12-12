"""Data coordinator for Barcode Router."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .backends.grocy import GrocyBackend
from .batch_manager import BatchManager

_LOGGER = logging.getLogger(__name__)


class BarcodeRouterCoordinator(DataUpdateCoordinator):
    """Coordinator for Barcode Router integration."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Barcode Router",
            update_interval=None,  # We don't need periodic updates
        )
        self.entry = entry
        self.batch_manager = BatchManager(hass)
        self.backends: dict[str, Any] = {}

        # Initialize Grocy backend
        grocy_config = {
            "url": entry.data.get("grocy_url", ""),
            "api_key": entry.data.get("grocy_api_key", ""),
        }
        self.backends["grocy"] = GrocyBackend(grocy_config)

    async def async_config_entry_first_refresh(self) -> None:
        """Load batch data on first refresh."""
        await self.batch_manager.load()
        await super().async_config_entry_first_refresh()

    async def _async_update_data(self) -> dict[str, Any]:
        """Update coordinator data."""
        # Return current batch state
        return {
            "batch": self.batch_manager.get_batch_data(),
            "backends": list(self.backends.keys()),
        }

    async def async_shutdown(self) -> None:
        """Shutdown coordinator and close backends."""
        # Close backend sessions
        for backend in self.backends.values():
            if hasattr(backend, "close"):
                await backend.close()
        await super().async_shutdown()
