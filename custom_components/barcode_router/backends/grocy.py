"""Grocy backend adapter."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .base import BackendBase

_LOGGER = logging.getLogger(__name__)


class GrocyBackend(BackendBase):
    """Grocy backend adapter."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize Grocy backend."""
        super().__init__(config)
        self.url = config.get("url", "").rstrip("/")
        self.api_key = config.get("api_key", "")
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _request(
        self, method: str, endpoint: str, **kwargs: Any
    ) -> dict[str, Any] | None:
        """Make a request to Grocy API."""
        session = await self._get_session()
        headers = {"GROCY-API-KEY": self.api_key, "Content-Type": "application/json"}
        url = f"{self.url}/api{endpoint}"

        try:
            async with session.request(
                method, url, headers=headers, timeout=aiohttp.ClientTimeout(total=10), **kwargs
            ) as response:
                if response.status == 404:
                    return None
                response.raise_for_status()
                if response.content_type == "application/json":
                    return await response.json()
                return None
        except aiohttp.ClientError as err:
            _LOGGER.error("Grocy API error: %s", err)
            raise

    async def check_item_exists(self, barcode: str) -> bool:
        """Check if an item exists in Grocy."""
        try:
            result = await self._request("GET", f"/objects/products/by-barcode/{barcode}")
            return result is not None
        except Exception as err:
            _LOGGER.error("Error checking item existence: %s", err)
            return False

    async def get_item_info(self, barcode: str) -> dict[str, Any] | None:
        """Get item information from Grocy."""
        try:
            product = await self._request("GET", f"/objects/products/by-barcode/{barcode}")
            if product is None:
                return None

            # Get product details
            product_id = product.get("id")
            if product_id:
                product_details = await self._request("GET", f"/objects/products/{product_id}")
                if product_details:
                    return {
                        "id": product_details.get("id"),
                        "name": product_details.get("name"),
                        "description": product_details.get("description"),
                        "barcode": barcode,
                        "unit": product_details.get("qu_unit_purchase", {}).get("name"),
                    }
            return product
        except Exception as err:
            _LOGGER.error("Error getting item info: %s", err)
            return None

    async def add_quantity(
        self, barcode: str, quantity: int, **kwargs: Any
    ) -> bool:
        """Add quantity to an existing item in Grocy."""
        try:
            # Get product by barcode
            product = await self._request("GET", f"/objects/products/by-barcode/{barcode}")
            if product is None:
                _LOGGER.error("Product not found for barcode: %s", barcode)
                return False

            product_id = product.get("id")
            if not product_id:
                _LOGGER.error("Product ID not found for barcode: %s", barcode)
                return False

            # Prepare booking data
            booking_data = {
                "amount": quantity,
                "product_id": product_id,
            }

            # Add optional fields if provided
            if "best_before_date" in kwargs:
                booking_data["best_before_date"] = kwargs["best_before_date"]
            if "purchased_date" in kwargs:
                booking_data["purchased_date"] = kwargs["purchased_date"]
            if "price" in kwargs:
                booking_data["price"] = kwargs["price"]
            if "shopping_location_id" in kwargs:
                booking_data["shopping_location_id"] = kwargs["shopping_location_id"]

            result = await self._request("POST", "/stock/bookin", json=booking_data)
            return result is not None
        except Exception as err:
            _LOGGER.error("Error adding quantity: %s", err)
            return False

    async def create_item(self, item_data: dict[str, Any]) -> bool:
        """Create a new item in Grocy."""
        try:
            # Prepare product data
            product_data = {
                "name": item_data.get("name", ""),
                "description": item_data.get("description", ""),
            }

            # Add optional fields
            if "qu_id_purchase" in item_data:
                product_data["qu_id_purchase"] = item_data["qu_id_purchase"]
            if "qu_id_stock" in item_data:
                product_data["qu_id_stock"] = item_data["qu_id_stock"]
            if "qu_factor_purchase_to_stock" in item_data:
                product_data["qu_factor_purchase_to_stock"] = item_data["qu_factor_purchase_to_stock"]
            if "location_id" in item_data:
                product_data["location_id"] = item_data["location_id"]
            if "shopping_location_id" in item_data:
                product_data["shopping_location_id"] = item_data["shopping_location_id"]

            # Create product
            product = await self._request("POST", "/objects/products", json=product_data)
            if product is None:
                return False

            product_id = product.get("id")
            if not product_id:
                return False

            # Link barcode to product
            barcode = item_data.get("barcode")
            if barcode:
                barcode_data = {
                    "product_id": product_id,
                    "barcode": barcode,
                }
                await self._request("POST", "/objects/product_barcodes", json=barcode_data)

            # If quantity is provided, add initial stock
            if "quantity" in item_data and item_data["quantity"] > 0:
                await self.add_quantity(
                    barcode,
                    item_data["quantity"],
                    best_before_date=item_data.get("best_before_date"),
                    purchased_date=item_data.get("purchased_date"),
                )

            return True
        except Exception as err:
            _LOGGER.error("Error creating item: %s", err)
            return False

    def get_required_fields(self) -> list[dict[str, str]]:
        """Get list of required fields for creating a new item in Grocy."""
        return [
            {"name": "name", "label": "Product Name", "type": "text", "required": True},
            {"name": "description", "label": "Description", "type": "text", "required": False},
            {"name": "quantity", "label": "Initial Quantity", "type": "number", "required": False},
            {"name": "best_before_date", "label": "Best Before Date", "type": "date", "required": False},
            {"name": "purchased_date", "label": "Purchase Date", "type": "date", "required": False},
        ]

    def get_backend_name(self) -> str:
        """Get the name of this backend."""
        return "Grocy"

    async def close(self) -> None:
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()
