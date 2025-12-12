"""UPC lookup service using upcitemdb.com."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import UPC_LOOKUP_API_URL

_LOGGER = logging.getLogger(__name__)

# Cache for UPC lookups
_upc_cache: dict[str, dict[str, Any]] = {}


async def lookup_barcode(barcode: str, use_cache: bool = True) -> dict[str, Any] | None:
    """Lookup barcode information from upcitemdb.com.

    Args:
        barcode: The barcode to lookup
        use_cache: Whether to use cached results

    Returns:
        Dictionary with product information or None if not found
    """
    # Check cache first
    if use_cache and barcode in _upc_cache:
        _LOGGER.debug("Using cached result for barcode: %s", barcode)
        return _upc_cache[barcode]

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                UPC_LOOKUP_API_URL,
                params={"upc": barcode},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status != 200:
                    _LOGGER.warning("UPC lookup returned status %d for barcode: %s", response.status, barcode)
                    return None

                data = await response.json()
                items = data.get("items", [])

                if not items:
                    _LOGGER.debug("No items found for barcode: %s", barcode)
                    return None

                # Use the first item
                item = items[0]
                result = {
                    "barcode": barcode,
                    "title": item.get("title", ""),
                    "brand": item.get("brand", ""),
                    "model": item.get("model", ""),
                    "category": item.get("category", ""),
                    "description": item.get("description", ""),
                    "images": item.get("images", []),
                    "offers": item.get("offers", []),
                }

                # Cache the result
                if use_cache:
                    _upc_cache[barcode] = result

                return result
    except aiohttp.ClientError as err:
        _LOGGER.error("Error looking up barcode %s: %s", barcode, err)
        return None
    except Exception as err:
        _LOGGER.exception("Unexpected error looking up barcode %s: %s", barcode, err)
        return None


def clear_cache() -> None:
    """Clear the UPC lookup cache."""
    global _upc_cache
    _upc_cache.clear()
    _LOGGER.debug("UPC lookup cache cleared")
