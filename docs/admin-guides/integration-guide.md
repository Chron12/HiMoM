# Integration Guide

## Overview

PreRollTracker and ApexAPI are two complementary applications that work together to manage the full lifecycle of cannabis pre-roll production and wholesale distribution. PreRollTracker handles production tracking (grinding, rolling, testing, packaging), while ApexAPI handles order management, inventory sync, and delivery logistics through the Apex Trading platform.

This guide explains how the two systems communicate, how data flows between them, how to set up the integration, and how to troubleshoot problems when things go wrong.

---

## 1. How PreRollTracker and ApexAPI Work Together

### 1.1 Role of Each Application

| Application | Primary Role | Runs On | Data Source |
|---|---|---|---|
| PreRollTracker | Production tracking, METRC compliance, finished goods inventory | Linux web server (himomstats.online) | Manual production data entry, weight checks |
| ApexAPI | Order management, Apex Trading integration, inventory sync | Windows desktop (per workstation) | Apex Trading API, PreRollTracker API |

### 1.2 The Big Picture

1. **Production staff** use PreRollTracker (via web browser) to track pre-roll production: how much flower goes in, how many pre-rolls come out, what stage each batch is at.
2. **METRC finished goods packages** are tracked in PreRollTracker with gram-level precision. As pre-rolls are packed against orders, grams are deducted from the appropriate METRC package.
3. **Wholesale orders** come in through Apex Trading. ApexAPI pulls these orders and displays them for fulfillment.
4. **ApexAPI reads production data** from PreRollTracker via its API to understand how many pre-rolls are available per strain and size.
5. **Batch inventory sync** in ApexAPI updates Apex Trading's batch quantities to match what is actually available based on PreRollTracker's finished goods data.
6. **Google Sheets** (optional) provides a shared packing list that production and fulfillment teams can both see and edit.

### 1.3 What Connects Them

The connection between the two systems is an HTTP API:

- **ApexAPI** acts as the **client**. It makes HTTP GET and POST requests.
- **PreRollTracker** acts as the **server**. It exposes API endpoints that return JSON data.
- **Authentication** uses an API key sent in the `X-API-Key` HTTP header.
- **Base URL:** `https://himomstats.online`

---

## 2. Data Flow Diagram

The following text-based diagram shows how data moves between all components:

```
+-------------------+          +-------------------+
|                   |          |                   |
|   Apex Trading    |<-------->|     ApexAPI        |
|   (Cloud API)     |  Orders  |  (Windows Desktop) |
|                   |  Batches |                   |
+-------------------+          +--------+----------+
                                        |
                                        | Dashboard API Key
                                        | (X-API-Key header)
                                        |
                                        v
                               +--------+----------+
                               |                   |
                               |  PreRollTracker    |
                               |  (himomstats.online)|
                               |                   |
                               +--------+----------+
                                        |
                                        | Manual Data Entry
                                        | (Web Browser)
                                        |
                                        v
                               +--------+----------+
                               |                   |
                               |  Production Staff  |
                               |                   |
                               +-------------------+


Data Flow Detail:

  Apex Trading ----[Orders, Products]----> ApexAPI
  ApexAPI ----[Batch Quantity Updates]----> Apex Trading
  ApexAPI ----[Read Batches, Inventory]----> PreRollTracker
  ApexAPI ----[SKU Breakdown, Sync Data]----> PreRollTracker
  PreRollTracker ----[Available Grams, Batch Data]----> ApexAPI
  Production Staff ----[Batch Updates, Weight Checks]----> PreRollTracker


Optional Google Sheets Integration:

  ApexAPI ----[Packing List, History]----> Google Sheets
  Google Sheets ----[Packed Quantities]----> ApexAPI
  Production Staff ----[Manual PACKED Updates]----> Google Sheets
```

### 2.1 Data Flow Summary

| Direction | What Flows | Protocol | Frequency |
|---|---|---|---|
| Apex Trading -> ApexAPI | Orders, product catalog | HTTPS (Bearer token) | Every 2 min (cache warming) |
| ApexAPI -> Apex Trading | Batch quantity updates | HTTPS PATCH (Bearer token) | Every 5 sec (batch sync) |
| ApexAPI -> PreRollTracker | Read active batches, finished goods | HTTPS GET (API key) | Every 5 sec (sync poll) |
| PreRollTracker -> ApexAPI | Available grams per METRC package, calculated units | HTTPS JSON response | On-demand via `/apex-calculate` |
| ApexAPI -> Google Sheets | Packing list data, history archives | Google Sheets API | Configurable (2 sec poll) |
| Google Sheets -> ApexAPI | Packed quantities (bidirectional) | Google Sheets API | Configurable |

---

## 3. Setting Up the Dashboard API Key Connection

### 3.1 Prerequisites

Before setting up the integration:

1. PreRollTracker must be running and accessible at `https://himomstats.online`.
2. You must have admin access to PreRollTracker to obtain the API key.
3. ApexAPI must be installed on the Windows workstation.

### 3.2 Step-by-Step Setup

1. **Log in to PreRollTracker** in your web browser at `https://himomstats.online`.
2. Navigate to **Settings**.
3. Locate the **API Key** section. The key is a long alphanumeric string (UUID format or token format).
4. **Copy the API key** to your clipboard.
5. On the Windows machine, navigate to the ApexAPI installation folder (typically on the Desktop or in Program Files).
6. Open `apex_config.json` in a text editor (Notepad is fine).
7. Find the `"dashboard_api_key"` line and paste your key:
   ```json
   "dashboard_api_key": "45cf0a80-7502-4cbb-884d-83875fbc2190"
   ```
8. Save the file.
9. **Restart ApexAPI** (close and reopen the application).
10. Check the connection status indicator in ApexAPI. It should show a green "Connected" status.

![PreRollTracker Settings page with the API key visible and a copy button highlighted](../screenshots/settings-api-key.png)

[SCREENSHOT: ApexAPI main window showing green connection status for the Dashboard]

### 3.3 Verifying the Connection

ApexAPI tests the connection by calling `GET /api/overview` on PreRollTracker. A successful connection returns the number of active batches.

If the connection fails:

1. Verify the API key is correct (no extra spaces or line breaks).
2. Verify PreRollTracker is accessible from the Windows machine: open a browser and go to `https://himomstats.online`.
3. Check the ApexAPI logs in the `logs/` directory for detailed error messages.
4. If the API key was recently regenerated on PreRollTracker, update the `dashboard_api_key` in `apex_config.json`.

---

## 4. METRC Number Mapping and Batch Sync

### 4.1 The Mapping Challenge

The core integration challenge is that the two systems identify products differently:

- **PreRollTracker** tracks finished goods by **METRC number** (a state compliance tracking number like `1A406030001234567890`). Each METRC package has a strain, initial grams, and current available grams.
- **Apex Trading** tracks inventory by **batch ID** (an integer assigned by Apex). Each batch has a product name that includes the strain and size info.

There is no direct link between a METRC number in PreRollTracker and a batch ID in Apex Trading. The `source_tag` field on Apex batches is often empty.

### 4.2 How the Mapping Works

ApexAPI's **BatchMappingService** bridges this gap using **strain name matching**:

1. **Fetch all batches** from Apex Trading's API.
2. **Filter to relevant products**: Only pre-roll products, CannaDarts, Magnetic Boxes, and Cocoa Blunts are included. The filter patterns are:
   - `cannadart`
   - `magnetic.*box` or `mag.*box`
   - `cocoa.*blunt`
3. **Extract strain name** from the Apex product name. For example, from "CannaDart - Blue Dream 0.5g" the service extracts "Blue Dream".
4. **Build a mapping**: strain name -> list of BatchInfo objects (one per SKU type).
5. **Match against PreRollTracker**: When syncing, the service matches a METRC package's strain to the corresponding Apex batches.

### 4.3 SKU Types and Grams Per Unit

The mapping service understands various SKU formats:

| SKU Pattern | Example | Grams Per Unit | Pack Count |
|---|---|---|---|
| `singles_0_5g` | "CannaDart - Blue Dream 0.5g" | 0.5 | 1 |
| `singles_1g` or `singles_1_0g` | "CannaDart - Blue Dream 1g" | 1.0 | 1 |
| `box_0_5g_6pk` | "Magnetic Box - Blue Dream 6pk" | 0.5 | 6 |
| `box_0_5g_12pk` | "Magnetic Box - Blue Dream 12pk" | 0.5 | 12 |
| `custom_cocoa_blunt_1_0g` | "Cocoa Blunt - Blue Dream 1g" | 1.0 | 1 |

### 4.4 The Sync Process

When batch inventory sync runs (every 5 seconds by default):

1. ApexAPI calls PreRollTracker's `/apex-calculate` endpoint.
2. PreRollTracker returns, for each METRC package, the calculated available units per SKU type (accounting for orders, packed amounts, and manual exclusions).
3. ApexAPI uses the BatchMappingService to find the corresponding Apex batch ID for each SKU type.
4. ApexAPI sends a `PATCH /api/v2/batches/{id}` request to Apex Trading to update the quantity.
5. State is tracked to avoid redundant updates (if quantities have not changed, the API call is skipped).

```
PreRollTracker                    ApexAPI                     Apex Trading
     |                              |                              |
     |  GET /apex-calculate         |                              |
     |<-----------------------------|                              |
     |  {metrc_1: {0.5g: 200,      |                              |
     |   1g: 100}, ...}             |                              |
     |----------------------------->|                              |
     |                              |  BatchMappingService:        |
     |                              |  strain -> batch_ids         |
     |                              |                              |
     |                              |  PATCH /api/v2/batches/123   |
     |                              |  {quantity: 200}             |
     |                              |----------------------------->|
     |                              |                              |
     |                              |  PATCH /api/v2/batches/456   |
     |                              |  {quantity: 100}             |
     |                              |----------------------------->|
```

### 4.5 Cache TTL

The batch mapping cache refreshes every 5 minutes (300 seconds). This means:

- If a new batch is created in Apex Trading, it may take up to 5 minutes to appear in the mapping.
- If a batch is deleted, it may take up to 5 minutes for sync to stop trying to update it.

### 4.6 Finished Goods Apex Integration Deep Dive

The Finished Goods system in PreRollTracker drives the Apex inventory numbers that stores see. Understanding how unit counts are calculated is critical for troubleshooting.

#### How `/apex-calculate` Works

When ApexAPI (or the Finished Goods page) requests calculated units for a package, PreRollTracker's `calculate_apex_units()` method runs:

1. **Determine effective grams:** If a physical inventory override is set, use that. Otherwise, use the METRC `current_grams`.
2. **Subtract all commitments:** Deduct `grams_ordered` (reserved), `grams_packed` (fulfilled), and wholesale holds from effective grams to get the truly available amount.
3. **For each SKU type:** Divide available grams by grams-per-unit to get unit count.
4. **Apply SKU settings:** Check per-package settings:
   - If `excluded = true` for a SKU, set its count to 0 (it won't appear in Apex).
   - If `manual_units` is set (not null), use that number instead of the calculated count.
5. **Include custom SKUs:** If the package has custom SKU definitions (CannaDart, Cocoa Blunt, etc.), calculate units for those too using their custom grams-per-unit.
6. **Return** the final unit counts per SKU.

#### Per-Package Apex SKU Settings

Each package can have individual SKU settings stored in `apex_sku_settings` JSON:

```json
{
  "singles_0_5g": {"excluded": false, "manual_units": null},
  "singles_1g": {"excluded": true, "manual_units": null},
  "magnetic_box_6pk": {"excluded": false, "manual_units": 50},
  "magnetic_box_12pk": {"excluded": false, "manual_units": null}
}
```

- `excluded: true` — SKU does not appear in Apex Trading for this package.
- `manual_units: 50` — Overrides the calculated count with exactly 50 units. Useful when auto-calculation doesn't match reality (damaged product, special allocations).

To configure via API: `POST /api/finished-goods/{metrc_number}/apex-settings`

#### Idempotent Decrement for Apex Sales

When a store sells a unit through Apex, the system sends a decrement to PreRollTracker:

```
POST /api/finished-goods/{metrc_number}/apex-decrement
{
  "sku": "singles_0_5g",
  "units": 1,
  "idempotency_key": "apex-sale-12345"
}
```

The `idempotency_key` prevents double-counting. If the same key is sent twice (network retry, duplicate webhook), the second request is ignored. Processed keys are stored in the package's `processed_decrements` JSON field.

#### Custom SKUs

Custom SKUs extend the default four SKU types. They are defined per-package:

```json
{
  "cannadart_0_8g": {"name": "CannaDart", "grams_per_unit": 0.8, "pack_size": 1},
  "cocoa_blunt_1g": {"name": "Cocoa Blunt", "grams_per_unit": 1.0, "pack_size": 1}
}
```

Managed via: `POST/PUT/DELETE /api/finished-goods/{metrc_number}/custom-skus`

#### Troubleshooting Apex Sync for Finished Goods

| Problem | Cause | Fix |
|---------|-------|-----|
| Package shows 0 units in Apex despite having grams | All SKUs are excluded in settings | Check Apex SKU settings, unexclude at least one SKU |
| Apex shows stale numbers | 5-minute cache TTL | Wait for refresh, or restart ApexAPI to force |
| Units suddenly dropped to 0 | Package was archived or orphaned | Check package status on Finished Goods page |
| Decrement applied twice | Missing idempotency key | Always send unique idempotency keys with decrements |
| Wrong unit counts after physical count | Override not set | Set physical inventory override to the actual grams |
| Custom SKU not showing in Apex | SKU not mapped in ApexAPI | Verify custom SKU is added on the package AND has a matching Apex batch |

---

## 5. Google Sheets Integration Setup

### 5.1 Overview

ApexAPI can sync packing list data to Google Sheets for shared visibility between the production floor and the office. The integration uses a three-sheet architecture:

| Sheet | Direction | Purpose |
|---|---|---|
| Packing List | Bidirectional | Active orders with PACKED quantities. Production edits PACKED counts; ApexAPI adds new orders. |
| History Sheet | Write-only | Archives completed items grouped by week. |
| Delivery Sheet | Write-only | Customer-facing delivery information. |

### 5.2 Prerequisites

1. A Google Cloud project with the Google Sheets API enabled.
2. A service account with credentials (JSON key file).
3. The target Google Spreadsheet shared with the service account's email address.

### 5.3 Setup Steps

1. **Create a Google Cloud Project** (if you do not already have one):
   - Go to https://console.cloud.google.com
   - Create a new project or select an existing one.
   - Enable the "Google Sheets API" from the API Library.

2. **Create a Service Account:**
   - In the Google Cloud Console, go to IAM & Admin > Service Accounts.
   - Create a new service account.
   - Download the JSON credentials file.
   - Place the file in a secure location accessible to ApexAPI (e.g., the ApexAPI folder).

3. **Create the Google Spreadsheet:**
   - Create a new Google Sheets document for the packing list.
   - Share it with the service account email (found in the JSON file under `client_email`). Give it "Editor" access.
   - Note the spreadsheet ID from the URL: `https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit`

4. **Configure ApexAPI:**
   - Open `apex_config.json`.
   - Add or update the Google Sheets configuration (this may need to be added manually if it does not exist):
   ```json
   "google_sheets": {
       "enabled": true,
       "credentials_path": "path/to/credentials.json",
       "packing_list_sheet_id": "your-spreadsheet-id",
       "history_sheet_id": "",
       "delivery_sheet_id": "",
       "poll_interval_seconds": 2,
       "fallback_to_excel": true,
       "auto_create_sheets": true
   }
   ```

5. **Restart ApexAPI.** The application will create the required sheet tabs (Packing List, History, Delivery) automatically if `auto_create_sheets` is `true`.

### 5.4 Sheet Column Layout

**Packing List columns:**

| Column | Content | Editable by |
|---|---|---|
| Product | Product name | ApexAPI (auto-populated) |
| Store | Customer/store name | ApexAPI |
| Ordered | Quantity ordered | ApexAPI |
| PACKED | Quantity packed | Production staff (manual) |
| Needs Production | Calculated shortfall | Formula |
| Needs Packing | Calculated packing need | Formula |
| Delivery Date | Target delivery date | Production staff |
| Delivery Notes | Notes about delivery | Production staff |
| Internal Notes | Internal team notes | Anyone |
| Invoice # | Apex order invoice number | ApexAPI |
| Batch # | METRC batch identifier | ApexAPI |
| Date | Order date | ApexAPI |

### 5.5 Fallback Behavior

If Google Sheets is unavailable (credentials missing, API error, network issue), ApexAPI falls back to local Excel file operation when `fallback_to_excel` is `true`. This ensures packing list functionality is not completely lost during outages.

---

## 6. Troubleshooting Sync Issues

### 6.1 Dashboard Connection Fails

**Symptom:** ApexAPI shows "Cannot connect to dashboard" or connection status is red.

**Diagnosis:**

1. Check if PreRollTracker is up: Open `https://himomstats.online` in a browser on the same machine.
2. Check the API key: Compare `dashboard_api_key` in `apex_config.json` with the key shown in PreRollTracker's Settings page.
3. Check the ApexAPI logs for the specific error message (timeout, 401, connection refused).

**Resolution:**

| Error | Cause | Fix |
|---|---|---|
| Connection refused | PreRollTracker is not running | Restart the service: `sudo systemctl start preroll-tracker` |
| 401 Unauthorized | API key mismatch | Copy the correct key from PreRollTracker Settings |
| Timeout | Network issue or slow server | Check server load and network connectivity |
| SSL error | Certificate problem | Verify HTTPS certificate is valid |

### 6.2 Batch Sync Not Updating Apex Trading

**Symptom:** Pre-rolls are packed in PreRollTracker, but Apex Trading inventory does not change.

**Diagnosis:**

1. Check if batch sync is enabled: Verify `batch_inventory_sync.enabled` is `true` in `apex_config.json`.
2. Check the ApexAPI sync status indicator in the application.
3. Check logs for "batch_inventory_sync" messages.

**Common causes:**

| Issue | Explanation | Fix |
|---|---|---|
| Strain name mismatch | The strain name in PreRollTracker does not match any Apex product | Verify strain naming is consistent across both systems |
| No matching Apex batch | No pre-roll batch exists in Apex for that strain | Create the batch in Apex Trading |
| Cache stale | The batch mapping has not refreshed yet | Wait 5 minutes or restart ApexAPI |
| Sync disabled | `batch_inventory_sync.enabled` is `false` | Set to `true` and restart |
| API token expired | Apex Trading token is no longer valid | Generate a new token in Apex Trading |

### 6.3 Orders Not Appearing in ApexAPI

**Symptom:** New orders placed in Apex Trading do not show up in ApexAPI.

**Diagnosis:**

1. Check if auto-refresh is enabled: `auto_refresh_enabled` should be `true`.
2. Check the Apex Trading API token: Is it still valid?
3. Check the `excluded_statuses` list: Is the order's status being filtered out?
4. Check the `api_initial_sync_date`: Orders before this date are ignored.

**Resolution:**

1. If the token is expired, generate a new one in Apex Trading and update `api_token` in `apex_config.json`.
2. If the order status is in `excluded_statuses`, remove that status from the list (or change the order status in Apex Trading).
3. If the order is older than `api_initial_sync_date`, adjust the date backward.

### 6.4 Google Sheets Not Syncing

**Symptom:** The Google Sheet is not being updated with new orders or packed quantities are not syncing back.

**Diagnosis:**

1. Check if Google Sheets integration is enabled in `apex_config.json`.
2. Verify the credentials file exists at the configured path.
3. Check that the spreadsheet is shared with the service account.
4. Check ApexAPI logs for Google Sheets API errors.

**Common errors:**

| Error | Cause | Fix |
|---|---|---|
| `credentials.json not found` | Wrong path in config | Correct the `credentials_path` |
| `403 Forbidden` | Sheet not shared with service account | Share with the service account email |
| `404 Not Found` | Wrong spreadsheet ID | Verify the `sheet_id` matches the URL |
| `Rate limit exceeded` | Too many API calls | Increase `poll_interval_seconds` |

---

## 7. Understanding the Batch Mapping Process

### 7.1 From Strain to Batch ID

The batch mapping process is the core algorithm that bridges PreRollTracker and Apex Trading. Here is how it works step by step:

1. **ApexAPI fetches all active batches** from Apex Trading via `GET /api/v1/batches`.

2. **For each batch**, the PreRollProductParser analyzes the product name to extract:
   - The strain name (e.g., "Blue Dream")
   - The unit size (e.g., 0.5g, 1.0g)
   - The pack configuration (single, 6-pack, 12-pack)
   - The product type (CannaDart, Magnetic Box, Cocoa Blunt)

3. **The mapping is built** as a dictionary: `{strain_name: [BatchInfo, BatchInfo, ...]}`. One strain can have multiple BatchInfo entries representing different SKU types.

4. **When sync runs**, PreRollTracker provides available grams per METRC package per SKU type. ApexAPI looks up the strain of that METRC package in the mapping to find the corresponding Apex batch IDs.

5. **Each batch quantity is updated** via the Apex Trading API. The quantity is calculated by dividing available grams by grams-per-unit for that SKU.

### 7.2 Example Walkthrough

Suppose PreRollTracker has a finished goods package:

- METRC number: `1A40603000123456`
- Strain: "Wedding Cake"
- Available grams: 500g

And Apex Trading has these batches:

| Batch ID | Product Name | SKU Key |
|---|---|---|
| 1001 | "CannaDart - Wedding Cake 0.5g" | `singles_0_5g` |
| 1002 | "CannaDart - Wedding Cake 1g" | `singles_1_0g` |
| 1003 | "Magnetic Box - Wedding Cake 6pk" | `box_0_5g_6pk` |

PreRollTracker's `/apex-calculate` endpoint returns:

```json
{
    "1A40603000123456": {
        "strain": "Wedding Cake",
        "available_grams": 500,
        "units": {
            "singles_0_5g": 200,
            "singles_1_0g": 100,
            "box_0_5g_6pk": 33
        }
    }
}
```

ApexAPI then:

1. Looks up "Wedding Cake" in the batch mapping.
2. Finds batch 1001 for `singles_0_5g`, batch 1002 for `singles_1_0g`, batch 1003 for `box_0_5g_6pk`.
3. Sends `PATCH /api/v2/batches/1001 {quantity: 200}`.
4. Sends `PATCH /api/v2/batches/1002 {quantity: 100}`.
5. Sends `PATCH /api/v2/batches/1003 {quantity: 33}`.

### 7.3 When Mapping Fails

If the batch mapping service cannot find a match for a strain, it logs a warning and skips that METRC package. Common reasons for mapping failure:

- **Spelling differences:** "Wedding Cake" in PreRollTracker vs. "Wedding cake" in Apex (case sensitivity depends on normalization).
- **New strain:** A new strain was added to PreRollTracker but no corresponding batches exist in Apex Trading yet.
- **Product type mismatch:** The batch exists in Apex but is not a recognized pre-roll product type (not matching the sync patterns).

To resolve mapping failures:

1. Check the ApexAPI logs for "no batch found for strain" messages.
2. Verify the strain spelling matches exactly between both systems.
3. Create the missing batch in Apex Trading if needed.
4. Wait for the 5-minute cache to refresh (or restart ApexAPI).

---

## Summary

| Integration Task | How |
|---|---|
| Connect ApexAPI to PreRollTracker | Copy API key from Settings to `apex_config.json` |
| Verify connection | Check green status indicator in ApexAPI |
| Enable batch inventory sync | Set `batch_inventory_sync.enabled: true` |
| Set up Google Sheets | Create service account, share sheet, configure in `apex_config.json` |
| Troubleshoot sync | Check logs, verify strain names match, check API tokens |
| Force mapping refresh | Restart ApexAPI (clears 5-minute cache) |
| Regenerate API key | Settings page in PreRollTracker, then update `apex_config.json` |
