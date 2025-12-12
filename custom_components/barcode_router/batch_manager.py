"""Batch scanning state management."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DEFAULT_QUANTITY, DOMAIN, STORAGE_KEY, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)


class BatchItem:
    """Represents an item in a batch."""

    def __init__(self, data: dict[str, Any]) -> None:
        """Initialize batch item from data."""
        self.barcode = data.get("barcode", "")
        self.upc_data = data.get("upc_data", {})
        self.backend = data.get("backend", "")
        self.exists = data.get("exists", False)
        self.quantity = data.get("quantity", DEFAULT_QUANTITY)
        self.pending_confirmation = data.get("pending_confirmation", {})
        self.item_info = data.get("item_info")
        self.status = data.get("status", "pending")  # pending, confirmed, processed, error
        self.error_message = data.get("error_message")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "barcode": self.barcode,
            "upc_data": self.upc_data,
            "backend": self.backend,
            "exists": self.exists,
            "quantity": self.quantity,
            "pending_confirmation": self.pending_confirmation,
            "item_info": self.item_info,
            "status": self.status,
            "error_message": self.error_message,
        }


class BatchManager:
    """Manages batch scanning state."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize batch manager."""
        self.hass = hass
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._batch: dict[str, Any] = {"items": [], "mode": "batch"}

    async def load(self) -> None:
        """Load batch from storage."""
        try:
            data = await self._store.async_load()
            if data:
                self._batch = data
                _LOGGER.debug("Loaded batch with %d items", len(self._batch.get("items", [])))
        except Exception as err:
            _LOGGER.error("Error loading batch: %s", err)
            self._batch = {"items": [], "mode": "batch"}

    async def save(self) -> None:
        """Save batch to storage."""
        try:
            await self._store.async_save(self._batch)
            _LOGGER.debug("Saved batch with %d items", len(self._batch.get("items", [])))
        except Exception as err:
            _LOGGER.error("Error saving batch: %s", err)

    def add_item(
        self,
        barcode: str,
        upc_data: dict[str, Any] | None,
        backend: str,
        exists: bool,
        item_info: dict[str, Any] | None = None,
    ) -> BatchItem:
        """Add an item to the batch."""
        # Check if item already exists in batch
        for item_data in self._batch.get("items", []):
            if item_data.get("barcode") == barcode:
                # Update existing item
                item_data["quantity"] = item_data.get("quantity", DEFAULT_QUANTITY) + 1
                item_data["upc_data"] = upc_data or item_data.get("upc_data", {})
                item_data["backend"] = backend
                item_data["exists"] = exists
                item_data["item_info"] = item_info
                item_data["status"] = "pending"
                _LOGGER.debug("Updated existing item in batch: %s", barcode)
                return BatchItem(item_data)

        # Create new item
        item_data = {
            "barcode": barcode,
            "upc_data": upc_data or {},
            "backend": backend,
            "exists": exists,
            "quantity": DEFAULT_QUANTITY,
            "pending_confirmation": {} if not exists else None,
            "item_info": item_info,
            "status": "pending",
        }
        self._batch.setdefault("items", []).append(item_data)
        _LOGGER.debug("Added new item to batch: %s", barcode)
        return BatchItem(item_data)

    def get_items(self) -> list[BatchItem]:
        """Get all items in the batch."""
        return [BatchItem(item) for item in self._batch.get("items", [])]

    def get_item(self, barcode: str) -> BatchItem | None:
        """Get a specific item from the batch."""
        for item_data in self._batch.get("items", []):
            if item_data.get("barcode") == barcode:
                return BatchItem(item_data)
        return None

    def update_item(self, barcode: str, updates: dict[str, Any]) -> bool:
        """Update an item in the batch."""
        for item_data in self._batch.get("items", []):
            if item_data.get("barcode") == barcode:
                item_data.update(updates)
                return True
        return False

    def remove_item(self, barcode: str) -> bool:
        """Remove an item from the batch."""
        items = self._batch.get("items", [])
        for i, item_data in enumerate(items):
            if item_data.get("barcode") == barcode:
                items.pop(i)
                return True
        return False

    def clear(self) -> None:
        """Clear the batch."""
        self._batch = {"items": [], "mode": "batch"}
        _LOGGER.debug("Cleared batch")

    def get_batch_data(self) -> dict[str, Any]:
        """Get the raw batch data."""
        return self._batch.copy()

    def set_mode(self, mode: str) -> None:
        """Set batch mode (batch or single)."""
        self._batch["mode"] = mode

    def get_mode(self) -> str:
        """Get batch mode."""
        return self._batch.get("mode", "batch")
