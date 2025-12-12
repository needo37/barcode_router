"""Backend adapters for Barcode Router."""
from __future__ import annotations

from .base import BackendBase
from .grocy import GrocyBackend

__all__ = ["BackendBase", "GrocyBackend"]
