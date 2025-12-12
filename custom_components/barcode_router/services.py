"""Home Assistant services for Barcode Router."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv

from .backends.base import BackendBase
from .batch_manager import BatchItem
from .const import (
    DEFAULT_QUANTITY,
    DOMAIN,
    SERVICE_CLEAR_BATCH,
    SERVICE_PROCESS_BATCH,
    SERVICE_SCAN_BARCODE,
)
from .item_detector import detect_item_type
from .upc_lookup import lookup_barcode

_LOGGER = logging.getLogger(__name__)

SCAN_BARCODE_SCHEMA = vol.Schema(
    {
        vol.Required("barcode"): cv.string,
        vol.Optional("backend"): cv.string,  # Manual override
        vol.Optional("quantity", default=DEFAULT_QUANTITY): vol.Coerce(int),
    }
)

PROCESS_BATCH_SCHEMA = vol.Schema(
    {
        vol.Optional("item_overrides"): vol.Schema(
            {
                cv.string: vol.Schema(
                    {
                        vol.Optional("quantity"): vol.Coerce(int),
                        vol.Optional("pending_confirmation"): dict,
                    }
                )
            }
        )
    }
)


async def async_setup_services(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Set up services for Barcode Router."""

    @callback
    def get_coordinator() -> Any:
        """Get the coordinator for this config entry."""
        return hass.data[DOMAIN][entry.entry_id]

    async def handle_scan_barcode(call: ServiceCall) -> None:
        """Handle scan_barcode service call."""
        coordinator = get_coordinator()
        barcode = call.data.get("barcode", "").strip()
        manual_backend = call.data.get("backend")
        quantity = call.data.get("quantity", DEFAULT_QUANTITY)

        if not barcode:
            _LOGGER.error("No barcode provided")
            return

        _LOGGER.info("Scanning barcode: %s", barcode)

        # Lookup UPC
        upc_data = await lookup_barcode(barcode)
        if not upc_data:
            _LOGGER.warning("Could not lookup barcode: %s", barcode)
            # Still add to batch with minimal data
            upc_data = {"barcode": barcode, "title": "Unknown Item"}

        # Detect item type
        backend_type = detect_item_type(upc_data, manual_backend)
        _LOGGER.info("Detected backend: %s for barcode: %s", backend_type, barcode)

        # Get backend
        backend: BackendBase | None = coordinator.backends.get(backend_type)
        if not backend:
            _LOGGER.error("Backend %s not available", backend_type)
            return

        # Check if item exists
        exists = await backend.check_item_exists(barcode)
        item_info = None
        if exists:
            item_info = await backend.get_item_info(barcode)

        # Add to batch
        batch_item = coordinator.batch_manager.add_item(
            barcode=barcode,
            upc_data=upc_data,
            backend=backend_type,
            exists=exists,
            item_info=item_info,
        )
        batch_item.quantity = quantity
        coordinator.batch_manager.update_item(barcode, batch_item.to_dict())

        # Save batch
        await coordinator.batch_manager.save()
        await coordinator.async_request_refresh()

        _LOGGER.info(
            "Added barcode %s to batch (exists: %s, backend: %s)",
            barcode,
            exists,
            backend_type,
        )

    async def handle_process_batch(call: ServiceCall) -> None:
        """Handle process_batch service call."""
        coordinator = get_coordinator()
        item_overrides = call.data.get("item_overrides", {})

        batch_items = coordinator.batch_manager.get_items()
        if not batch_items:
            _LOGGER.warning("No items in batch to process")
            return

        _LOGGER.info("Processing batch with %d items", len(batch_items))

        results = []
        for item in batch_items:
            barcode = item.barcode
            backend_type = item.backend

            # Apply overrides if provided
            if barcode in item_overrides:
                overrides = item_overrides[barcode]
                if "quantity" in overrides:
                    item.quantity = overrides["quantity"]
                if "pending_confirmation" in overrides:
                    item.pending_confirmation = overrides["pending_confirmation"]

            # Get backend
            backend: BackendBase | None = coordinator.backends.get(backend_type)
            if not backend:
                _LOGGER.error("Backend %s not available for item %s", backend_type, barcode)
                coordinator.batch_manager.update_item(
                    barcode, {"status": "error", "error_message": f"Backend {backend_type} not available"}
                )
                results.append({"barcode": barcode, "success": False, "error": "Backend not available"})
                continue

            try:
                if item.exists:
                    # Add quantity to existing item
                    success = await backend.add_quantity(barcode, item.quantity)
                    if success:
                        coordinator.batch_manager.update_item(barcode, {"status": "processed"})
                        results.append({"barcode": barcode, "success": True, "action": "added_quantity"})
                        _LOGGER.info("Added quantity %d to item %s", item.quantity, barcode)
                    else:
                        coordinator.batch_manager.update_item(
                            barcode, {"status": "error", "error_message": "Failed to add quantity"}
                        )
                        results.append({"barcode": barcode, "success": False, "error": "Failed to add quantity"})
                else:
                    # Create new item
                    item_data = {
                        "barcode": barcode,
                        "name": item.upc_data.get("title", "Unknown Item"),
                        "description": item.upc_data.get("description", ""),
                        "quantity": item.quantity,
                    }
                    # Merge pending confirmation data
                    if item.pending_confirmation:
                        item_data.update(item.pending_confirmation)

                    success = await backend.create_item(item_data)
                    if success:
                        coordinator.batch_manager.update_item(barcode, {"status": "processed"})
                        results.append({"barcode": barcode, "success": True, "action": "created_item"})
                        _LOGGER.info("Created new item %s", barcode)
                    else:
                        coordinator.batch_manager.update_item(
                            barcode, {"status": "error", "error_message": "Failed to create item"}
                        )
                        results.append({"barcode": barcode, "success": False, "error": "Failed to create item"})
            except Exception as err:
                _LOGGER.exception("Error processing item %s: %s", barcode, err)
                coordinator.batch_manager.update_item(
                    barcode, {"status": "error", "error_message": str(err)}
                )
                results.append({"barcode": barcode, "success": False, "error": str(err)})

        # Save batch state
        await coordinator.batch_manager.save()
        await coordinator.async_request_refresh()

        _LOGGER.info("Batch processing complete: %d items processed", len(results))

    async def handle_clear_batch(call: ServiceCall) -> None:
        """Handle clear_batch service call."""
        coordinator = get_coordinator()
        coordinator.batch_manager.clear()
        await coordinator.batch_manager.save()
        await coordinator.async_request_refresh()
        _LOGGER.info("Batch cleared")

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_SCAN_BARCODE,
        handle_scan_barcode,
        schema=SCAN_BARCODE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_PROCESS_BATCH,
        handle_process_batch,
        schema=PROCESS_BATCH_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_BATCH,
        handle_clear_batch,
    )

    _LOGGER.info("Barcode Router services registered")
