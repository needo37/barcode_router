"""Constants for the Barcode Router integration."""
from __future__ import annotations

DOMAIN = "barcode_router"

# Service names
SERVICE_SCAN_BARCODE = "scan_barcode"
SERVICE_PROCESS_BATCH = "process_batch"
SERVICE_CLEAR_BATCH = "clear_batch"

# Backend types
BACKEND_GROCY = "grocy"
BACKEND_HOMEBOX = "homebox"
BACKEND_LIBRARY = "library"

# Configuration keys
CONF_GROCY_URL = "grocy_url"
CONF_GROCY_API_KEY = "grocy_api_key"
CONF_BACKENDS = "backends"

# State storage keys
STORAGE_KEY = f"{DOMAIN}_batch"
STORAGE_VERSION = 1

# UPC Lookup
UPC_LOOKUP_API_URL = "https://api.upcitemdb.com/prod/trial/lookup"

# Default values
DEFAULT_QUANTITY = 1
DEFAULT_BACKEND = BACKEND_GROCY
