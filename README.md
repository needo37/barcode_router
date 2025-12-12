# Barcode Router Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

A Home Assistant custom integration for barcode scanning that automatically detects item types and routes them to the appropriate backend (Grocy, Homebox, or future library apps).

## Features

- **Automatic Item Type Detection**: Uses UPC lookup data to automatically determine which backend to use
- **Batch Scanning**: Scan multiple items and process them all at once
- **Grocy Integration**: Full support for Grocy API (check existence, add quantity, create products)
- **Extensible Architecture**: Easy to add new backends (Homebox, library apps, etc.)
- **Simple UI**: Custom Lovelace card for easy scanning interface
- **USB Scanner Support**: Works with USB barcode scanners that act as keyboards

## Installation

### HACS (Recommended)

1. Make sure [HACS](https://hacs.xyz/) is installed in your Home Assistant instance
2. Go to **HACS** → **Integrations**
3. Click the three dots in the top right corner → **Custom repositories**
4. Add this repository:
   - Repository: `https://github.com/needo37/barcode_router`
   - Category: **Integration**
5. Click **Add**
6. Search for "Barcode Router" in HACS
7. Click **Download**
8. Restart Home Assistant
9. Go to **Settings** → **Devices & Services** → **Add Integration**
10. Search for "Barcode Router" and follow the setup wizard:
    - Enter your Grocy URL (e.g., `http://grocy.local:9283`)
    - Enter your Grocy API key
    - Test connection

### Manual Installation

1. Download the latest release from the [Releases](https://github.com/needo37/barcode_router/releases) page
2. Extract the `custom_components` folder to your Home Assistant config directory
3. Restart Home Assistant
4. Go to **Settings** → **Devices & Services** → **Add Integration**
5. Search for "Barcode Router" and follow the setup wizard

## Configuration

The integration is configured through the Home Assistant UI during setup. The configuration requires:
- Grocy URL (e.g., `http://grocy.local:9283`)
- Grocy API key

## Usage

### Services

The integration provides three services:

#### `barcode_router.scan_barcode`
Scans a barcode and adds it to the batch.

**Service Data:**
- `barcode` (required): The barcode to scan
- `backend` (optional): Manual backend override (grocy, homebox, library)
- `quantity` (optional): Quantity to add (default: 1)

**Example:**
```yaml
service: barcode_router.scan_barcode
data:
  barcode: "0123456789012"
  quantity: 2
```

#### `barcode_router.process_batch`
Processes all items in the current batch.

**Service Data:**
- `item_overrides` (optional): Override specific item data before processing

**Example:**
```yaml
service: barcode_router.process_batch
data:
  item_overrides:
    "0123456789012":
      quantity: 3
      pending_confirmation:
        name: "Custom Product Name"
```

#### `barcode_router.clear_batch`
Clears all items from the current batch.

**Example:**
```yaml
service: barcode_router.clear_batch
```

### Lovelace Card

1. **Copy the card file** to your Home Assistant `www` folder:
   ```bash
   cp custom_components/barcode_router/www/barcode-scanner.js <config>/www/barcode-scanner.js
   ```

2. **Load the card resource** (one-time setup):
   - Go to **Settings** → **Dashboards** → **Resources** (or **Developer Tools** → **YAML** → **Lovelace Dashboards** → **Resources**)
   - Click **Add Resource** (or edit `ui-lovelace.yaml` if using YAML mode)
   - Set URL to: `/local/barcode-scanner.js`
   - Set Type to: **JavaScript Module**
   - Click **Create** (or save if using YAML)

3. **Add the card to your dashboard**:
   ```yaml
   type: custom:barcode-scanner-card
   ```

The card provides:
- Barcode input field (works with USB scanners)
- Real-time scan feedback
- Batch review panel
- Process and clear batch buttons
- Auto-refresh every 5 seconds when items are in batch

## How It Works

1. **Scan Barcode**: When you scan a barcode, the integration:
   - Looks up product information from upcitemdb.com
   - Automatically detects the item type (grocery, tool, book, etc.)
   - Checks if the item exists in the appropriate backend
   - Adds it to the batch

2. **Batch Review**: Review all scanned items, adjust quantities, and confirm new items

3. **Process Batch**: All items are sent to their respective backends:
   - Existing items: Quantity is added via purchase API
   - New items: Product is created with all details

## Item Type Detection

The integration automatically detects item types based on:
- UPC category data from upcitemdb.com
- Product title and description keywords
- Defaults to Grocy for groceries/consumables

### Category Mappings

- **Grocy**: Food, Beverages, Snacks, Dairy, Cleaning Supplies, Personal Care, etc.
- **Homebox**: Tools, Hardware, Electronics, Office Supplies, etc.
- **Library**: Books, Media, Movies, Music, Video Games, etc.

## Extending to New Backends

To add a new backend (e.g., Homebox):

1. Create a new file `backends/homebox.py`
2. Implement the `BackendBase` interface:
   ```python
   from .base import BackendBase
   
   class HomeboxBackend(BackendBase):
       async def check_item_exists(self, barcode: str) -> bool:
           # Implementation
           pass
       
       # ... implement other required methods
   ```
3. Register the backend in the coordinator
4. Update item type detection if needed

## Troubleshooting

### Integration not appearing in Add Integration
- Make sure HACS installation completed successfully
- Check Home Assistant logs for any errors
- Ensure you've restarted Home Assistant after installation

### Barcode not found in UPC database
- The integration will still add the item to the batch with minimal data
- You can manually enter product information when processing the batch

### Backend connection errors
- Check your Grocy URL and API key
- Verify Grocy is accessible from Home Assistant
- Check Home Assistant logs for detailed error messages

### USB Scanner not working
- USB scanners that act as keyboards should work automatically
- Make sure the input field is focused when scanning
- Some scanners may require configuration to add a newline after scan

## Requirements

- Home Assistant 2024.4 or later
- Python 3.13
- aiohttp library (installed automatically)

## License

This integration is provided as-is for personal use.
