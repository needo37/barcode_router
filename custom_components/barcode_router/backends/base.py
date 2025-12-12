"""Base class for backend adapters."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BackendBase(ABC):
    """Abstract base class for backend adapters."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the backend."""
        self.config = config

    @abstractmethod
    async def check_item_exists(self, barcode: str) -> bool:
        """Check if an item exists in the backend."""
        pass

    @abstractmethod
    async def get_item_info(self, barcode: str) -> dict[str, Any] | None:
        """Get item information from the backend."""
        pass

    @abstractmethod
    async def add_quantity(
        self, barcode: str, quantity: int, **kwargs: Any
    ) -> bool:
        """Add quantity to an existing item."""
        pass

    @abstractmethod
    async def create_item(self, item_data: dict[str, Any]) -> bool:
        """Create a new item in the backend."""
        pass

    @abstractmethod
    def get_required_fields(self) -> list[dict[str, str]]:
        """Get list of required fields for creating a new item."""
        pass

    @abstractmethod
    def get_backend_name(self) -> str:
        """Get the name of this backend."""
        pass
