/* eslint-disable @typescript-eslint/no-this-alias */
/* eslint-disable @typescript-eslint/no-explicit-any */
class BarcodeScannerCard extends HTMLElement {
  setConfig(config) {
    this.config = config;
  }

  set hass(hass) {
    this._hass = hass;
    this.updateCard();
  }

  async updateCard() {
    if (!this._hass) return;

    // Get batch data from coordinator
    const domain = "barcode_router";
    const domainData = this._hass.data[domain] || {};
    // Get first entry's coordinator (in most cases there's only one)
    const entryId = Object.keys(domainData)[0];
    const coordinator = entryId ? domainData[entryId] : null;
    const coordinatorData = coordinator?.data || {};
    const batchData = coordinatorData.batch || { items: [], mode: "batch" };
    const items = batchData.items || [];

    if (!this.content) {
      this.innerHTML = `
        <ha-card>
          <div class="card-content">
            <div class="header">
              <h2>Barcode Scanner</h2>
              <div class="header-actions">
                <button id="refresh-btn" class="refresh-button" title="Refresh">⟳</button>
                <div class="batch-info">
                  <span id="item-count">0</span> items in batch
                </div>
              </div>
            </div>
            <div class="scanner-section">
              <div class="input-group">
                <input
                  type="text"
                  id="barcode-input"
                  placeholder="Scan barcode or enter manually"
                  autocomplete="off"
                />
                <button id="scan-btn" class="scan-button">Scan</button>
              </div>
              <div id="scan-status" class="status-message"></div>
            </div>
            <div class="batch-section" id="batch-section" style="display: none;">
              <h3>Batch Review</h3>
              <div id="batch-items"></div>
              <div class="batch-actions">
                <button id="process-btn" class="process-button">Process Batch</button>
                <button id="clear-btn" class="clear-button">Clear Batch</button>
              </div>
            </div>
          </div>
        </ha-card>
      `;

      this.content = this.querySelector(".card-content");
      this.setupEventListeners();
    }

    // Update item count
    const itemCountEl = this.querySelector("#item-count");
    if (itemCountEl) {
      itemCountEl.textContent = items.length;
    }

    // Update batch section visibility
    const batchSection = this.querySelector("#batch-section");
    if (batchSection) {
      batchSection.style.display = items.length > 0 ? "block" : "none";
    }

    // Update batch items list
    this.updateBatchItems(items);
  }

  setupEventListeners() {
    const barcodeInput = this.querySelector("#barcode-input");
    const scanBtn = this.querySelector("#scan-btn");
    const processBtn = this.querySelector("#process-btn");
    const clearBtn = this.querySelector("#clear-btn");
    const refreshBtn = this.querySelector("#refresh-btn");

    // Scan button click
    if (scanBtn) {
      scanBtn.addEventListener("click", () => this.handleScan());
    }

    // Enter key in input
    if (barcodeInput) {
      barcodeInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
          this.handleScan();
        }
      });
      // Auto-focus for USB scanner
      barcodeInput.focus();
    }

    // Process batch
    if (processBtn) {
      processBtn.addEventListener("click", () => this.handleProcessBatch());
    }

    // Clear batch
    if (clearBtn) {
      clearBtn.addEventListener("click", () => this.handleClearBatch());
    }

    // Refresh
    if (refreshBtn) {
      refreshBtn.addEventListener("click", () => this.updateCard());
    }

    // Auto-refresh every 5 seconds if there are items in batch
    if (this._refreshInterval) {
      clearInterval(this._refreshInterval);
    }
    this._refreshInterval = setInterval(() => {
      const items = this.getBatchItems();
      if (items.length > 0) {
        this.updateCard();
      }
    }, 5000);
  }

  getBatchItems() {
    const domain = "barcode_router";
    const domainData = this._hass?.data[domain] || {};
    const entryId = Object.keys(domainData)[0];
    const coordinator = entryId ? domainData[entryId] : null;
    const coordinatorData = coordinator?.data || {};
    const batchData = coordinatorData.batch || { items: [], mode: "batch" };
    return batchData.items || [];
  }

  async handleScan() {
    const barcodeInput = this.querySelector("#barcode-input");
    const statusEl = this.querySelector("#scan-status");
    const barcode = barcodeInput?.value.trim();

    if (!barcode) {
      this.showStatus("Please enter a barcode", "error");
      return;
    }

    this.showStatus("Scanning...", "info");
    const scanBtn = this.querySelector("#scan-btn");
    if (scanBtn) scanBtn.disabled = true;

    try {
      await this._hass.callService("barcode_router", "scan_barcode", {
        barcode: barcode,
      });

      this.showStatus(`Scanned: ${barcode}`, "success");
      if (barcodeInput) {
        barcodeInput.value = "";
        barcodeInput.focus();
      }

      // Refresh card
      setTimeout(() => this.updateCard(), 500);
    } catch (error) {
      this.showStatus(`Error: ${error.message}`, "error");
    } finally {
      const scanBtn = this.querySelector("#scan-btn");
      if (scanBtn) scanBtn.disabled = false;
    }
  }

  async handleProcessBatch() {
    const processBtn = this.querySelector("#process-btn");
    if (processBtn) processBtn.disabled = true;

    try {
      await this._hass.callService("barcode_router", "process_batch", {});
      this.showStatus("Batch processed successfully!", "success");
      setTimeout(() => this.updateCard(), 1000);
    } catch (error) {
      this.showStatus(`Error processing batch: ${error.message}`, "error");
    } finally {
      if (processBtn) processBtn.disabled = false;
    }
  }

  async handleClearBatch() {
    if (!confirm("Clear all items from batch?")) return;

    try {
      await this._hass.callService("barcode_router", "clear_batch", {});
      this.showStatus("Batch cleared", "info");
      setTimeout(() => this.updateCard(), 500);
    } catch (error) {
      this.showStatus(`Error clearing batch: ${error.message}`, "error");
    }
  }

  updateBatchItems(items) {
    const batchItemsEl = this.querySelector("#batch-items");
    if (!batchItemsEl) return;

    if (items.length === 0) {
      batchItemsEl.innerHTML = "<p>No items in batch</p>";
      return;
    }

    batchItemsEl.innerHTML = items
      .map((item, index) => {
        const upcData = item.upc_data || {};
        const title = upcData.title || item.barcode;
        const backend = item.backend || "unknown";
        const exists = item.exists ? "✓ Exists" : "✗ New";
        const status = item.status || "pending";
        const quantity = item.quantity || 1;

        return `
          <div class="batch-item ${status}" data-index="${index}">
            <div class="item-header">
              <span class="item-title">${title}</span>
              <span class="item-badge ${item.exists ? "exists" : "new"}">${exists}</span>
            </div>
            <div class="item-details">
              <span class="item-barcode">${item.barcode}</span>
              <span class="item-backend">${backend}</span>
              <span class="item-quantity">Qty: ${quantity}</span>
            </div>
            ${status === "error" ? `<div class="error-message">${item.error_message || "Error"}</div>` : ""}
          </div>
        `;
      })
      .join("");
  }

  showStatus(message, type = "info") {
    const statusEl = this.querySelector("#scan-status");
    if (!statusEl) return;

    statusEl.textContent = message;
    statusEl.className = `status-message ${type}`;
    statusEl.style.display = "block";

    if (type === "success" || type === "info") {
      setTimeout(() => {
        statusEl.style.display = "none";
      }, 3000);
    }
  }

  getCardSize() {
    return 3;
  }
}

customElements.define("barcode-scanner-card", BarcodeScannerCard);

// Add styles
const style = document.createElement("style");
style.textContent = `
  .card-content {
    padding: 16px;
  }
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }
  .header-actions {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .refresh-button {
    background: none;
    border: none;
    font-size: 1.2em;
    cursor: pointer;
    padding: 4px 8px;
    color: var(--primary-text-color);
  }
  .refresh-button:hover {
    color: var(--primary-color);
  }
  .header h2 {
    margin: 0;
    font-size: 1.2em;
  }
  .batch-info {
    font-size: 0.9em;
    color: var(--secondary-text-color);
  }
  .scanner-section {
    margin-bottom: 24px;
  }
  .input-group {
    display: flex;
    gap: 8px;
    margin-bottom: 8px;
  }
  #barcode-input {
    flex: 1;
    padding: 12px;
    font-size: 16px;
    border: 1px solid var(--divider-color);
    border-radius: 4px;
  }
  .scan-button, .process-button, .clear-button {
    padding: 12px 24px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
  }
  .scan-button {
    background-color: var(--primary-color);
    color: var(--text-primary-color);
  }
  .process-button {
    background-color: var(--success-color, #4caf50);
    color: white;
  }
  .clear-button {
    background-color: var(--error-color, #f44336);
    color: white;
  }
  .status-message {
    padding: 8px;
    border-radius: 4px;
    margin-top: 8px;
    display: none;
  }
  .status-message.success {
    background-color: var(--success-color, #4caf50);
    color: white;
  }
  .status-message.error {
    background-color: var(--error-color, #f44336);
    color: white;
  }
  .status-message.info {
    background-color: var(--info-color, #2196f3);
    color: white;
  }
  .batch-section {
    margin-top: 24px;
    padding-top: 24px;
    border-top: 1px solid var(--divider-color);
  }
  .batch-item {
    padding: 12px;
    margin-bottom: 8px;
    border: 1px solid var(--divider-color);
    border-radius: 4px;
    background-color: var(--card-background-color);
  }
  .batch-item.processed {
    opacity: 0.6;
  }
  .batch-item.error {
    border-color: var(--error-color, #f44336);
  }
  .item-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }
  .item-title {
    font-weight: 500;
  }
  .item-badge {
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.8em;
  }
  .item-badge.exists {
    background-color: var(--success-color, #4caf50);
    color: white;
  }
  .item-badge.new {
    background-color: var(--warning-color, #ff9800);
    color: white;
  }
  .item-details {
    display: flex;
    gap: 12px;
    font-size: 0.9em;
    color: var(--secondary-text-color);
  }
  .error-message {
    margin-top: 8px;
    color: var(--error-color, #f44336);
    font-size: 0.9em;
  }
  .batch-actions {
    display: flex;
    gap: 8px;
    margin-top: 16px;
  }
`;
document.head.appendChild(style);
