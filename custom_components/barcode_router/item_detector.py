"""Automatic item type detection from UPC data."""
from __future__ import annotations

import logging
from typing import Any

from .const import BACKEND_GROCY, BACKEND_HOMEBOX, BACKEND_LIBRARY, DEFAULT_BACKEND

_LOGGER = logging.getLogger(__name__)

# Category mappings to backends
# These are common UPC categories that map to different backends
CATEGORY_MAPPINGS: dict[str, str] = {
    # Grocy categories (food, beverages, consumables)
    "Food": BACKEND_GROCY,
    "Beverages": BACKEND_GROCY,
    "Snacks": BACKEND_GROCY,
    "Dairy": BACKEND_GROCY,
    "Meat": BACKEND_GROCY,
    "Produce": BACKEND_GROCY,
    "Frozen": BACKEND_GROCY,
    "Bakery": BACKEND_GROCY,
    "Candy": BACKEND_GROCY,
    "Condiments": BACKEND_GROCY,
    "Spices": BACKEND_GROCY,
    "Canned Goods": BACKEND_GROCY,
    "Pasta": BACKEND_GROCY,
    "Cereal": BACKEND_GROCY,
    "Baby Food": BACKEND_GROCY,
    "Pet Food": BACKEND_GROCY,
    "Cleaning Supplies": BACKEND_GROCY,
    "Personal Care": BACKEND_GROCY,
    "Health & Beauty": BACKEND_GROCY,
    "Household": BACKEND_GROCY,
    # Homebox categories (tools, hardware, non-consumables)
    "Tools": BACKEND_HOMEBOX,
    "Hardware": BACKEND_HOMEBOX,
    "Electronics": BACKEND_HOMEBOX,
    "Home Improvement": BACKEND_HOMEBOX,
    "Automotive": BACKEND_HOMEBOX,
    "Office Supplies": BACKEND_HOMEBOX,
    "Stationery": BACKEND_HOMEBOX,
    "Kitchenware": BACKEND_HOMEBOX,
    "Home Decor": BACKEND_HOMEBOX,
    "Furniture": BACKEND_HOMEBOX,
    "Appliances": BACKEND_HOMEBOX,
    # Library categories (books, media)
    "Books": BACKEND_LIBRARY,
    "Media": BACKEND_LIBRARY,
    "Movies": BACKEND_LIBRARY,
    "Music": BACKEND_LIBRARY,
    "Video Games": BACKEND_LIBRARY,
    "Software": BACKEND_LIBRARY,
}


def detect_item_type(upc_data: dict[str, Any] | None, manual_override: str | None = None) -> str:
    """Detect item type from UPC data.

    Args:
        upc_data: Dictionary with UPC lookup results
        manual_override: Manual backend selection override

    Returns:
        Backend type string (grocy, homebox, library)
    """
    # Manual override takes precedence
    if manual_override:
        _LOGGER.debug("Using manual override: %s", manual_override)
        return manual_override

    # If no UPC data, default to Grocy
    if not upc_data:
        _LOGGER.debug("No UPC data, defaulting to %s", DEFAULT_BACKEND)
        return DEFAULT_BACKEND

    # Try to detect from category
    category = upc_data.get("category", "")
    if category:
        # Check exact match
        if category in CATEGORY_MAPPINGS:
            backend = CATEGORY_MAPPINGS[category]
            _LOGGER.debug("Detected backend %s from category: %s", backend, category)
            return backend

        # Check partial match (case-insensitive)
        category_lower = category.lower()
        for cat_key, backend in CATEGORY_MAPPINGS.items():
            if cat_key.lower() in category_lower or category_lower in cat_key.lower():
                _LOGGER.debug("Detected backend %s from partial category match: %s", backend, category)
                return backend

    # Try to detect from title/description keywords
    title = upc_data.get("title", "").lower()
    description = upc_data.get("description", "").lower()
    text = f"{title} {description}"

    # Library keywords
    library_keywords = ["book", "novel", "dvd", "cd", "blu-ray", "game", "software"]
    if any(keyword in text for keyword in library_keywords):
        _LOGGER.debug("Detected library backend from keywords")
        return BACKEND_LIBRARY

    # Homebox keywords
    homebox_keywords = ["tool", "screwdriver", "wrench", "hammer", "screw", "bolt", "hardware"]
    if any(keyword in text for keyword in homebox_keywords):
        _LOGGER.debug("Detected homebox backend from keywords")
        return BACKEND_HOMEBOX

    # Default to Grocy for everything else
    _LOGGER.debug("Defaulting to %s backend", DEFAULT_BACKEND)
    return DEFAULT_BACKEND


def get_available_backends() -> list[str]:
    """Get list of available backend types."""
    return [BACKEND_GROCY, BACKEND_HOMEBOX, BACKEND_LIBRARY]
