# PreRollTracker REST API Reference

**Base URL:** `https://himomstats.online` (production) or `http://localhost:5000` (development)

**Version:** 2.0.0

**Last Updated:** 2026-02-28

---

## Authentication

PreRollTracker supports two authentication methods:

### 1. Session-Based Authentication (Cookie)

Used by the web interface. Authenticate via `POST /login` to obtain a session cookie.

- Session cookies are `HttpOnly`, `SameSite=Lax`, and `Secure` in production.
- Sessions persist for 30 days when "Remember me" is selected.
- CSRF tokens are required for web form submissions (not API routes).

### 2. API Key Authentication (Header)

For programmatic access. Pass the API key in the `X-API-Key` header.

```
X-API-Key: your-api-key-here
```

- View your current API key: `GET /api/api-key` (session auth required)
- Regenerate API key: `POST /api/api-key/regenerate` (session auth required)
- API key validation uses constant-time comparison to prevent timing attacks.

### Authentication Error Responses

```json
{
  "error": "Authentication required"
}
```
**Status:** `401 Unauthorized`

```json
{
  "error": "Invalid API key"
}
```
**Status:** `401 Unauthorized`

### Auth Decorators

Endpoints are protected by one of two decorators:

| Decorator | Session Auth | API Key Auth | Description |
|-----------|-------------|-------------|-------------|
| `@login_required` | Yes | No | Web session only |
| `@api_or_login_required` | Yes | Yes | Either method accepted |

---

## Rate Limiting

The application uses `flask-limiter` with rate limiting configured per-endpoint. The default configuration does not apply global rate limits, but specific endpoints (login, forgot-password) have tighter limits to prevent brute-force attacks.

| Endpoint | Limit |
|----------|-------|
| `POST /login` | 5 per minute |
| `POST /forgot-password` | 2 per minute |
| `POST /reset-password` | 5 per minute |
| All other endpoints | No explicit limit |

**Max Request Size:** 16 MB (`MAX_CONTENT_LENGTH`)

---

## Common Error Responses

All API endpoints return errors in a consistent JSON format:

```json
{
  "error": "Description of the error"
}
```

| Status Code | Meaning |
|-------------|---------|
| 400 | Bad Request -- Invalid parameters or missing required fields |
| 401 | Unauthorized -- Authentication required or invalid |
| 403 | Forbidden -- Operation not allowed (e.g., archiving non-completed batch) |
| 404 | Not Found -- Resource does not exist |
| 413 | Payload Too Large -- Request body exceeds 16 MB |
| 500 | Internal Server Error -- Server-side error |

---

## AUTH Endpoints

### GET /login

Render the admin login page.

- **Auth Required:** No
- **Response:** HTML login form

```bash
curl https://himomstats.online/login
```

---

### POST /login

Authenticate and establish a session.

- **Auth Required:** No
- **Content-Type:** `application/x-www-form-urlencoded`
- **CSRF:** Required (via `csrf_token` hidden field)
- **Rate Limit:** 5 per minute

**Request Parameters (form body):**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `password` | string | Yes | Admin password |
| `remember_me` | string | No | Set to `"1"` for 30-day session |
| `csrf_token` | string | Yes | CSRF token from form |

**Success Response:** `302 Redirect` to `/admin`

**Error Response:** `400` with flashed message "Invalid password" (re-renders login form)

```bash
curl -X POST https://himomstats.online/login \
  -d "password=yourpassword&remember_me=1&csrf_token=TOKEN"
```

---

### GET /logout

Log out and clear the session.

- **Auth Required:** No (clears session if present)
- **Response:** `302 Redirect` to `/login`

```bash
curl https://himomstats.online/logout
```

---

### GET /forgot-password

Render the password recovery page.

- **Auth Required:** No
- **Response:** HTML form for recovery key entry

```bash
curl https://himomstats.online/forgot-password
```

---

### POST /forgot-password

Verify a recovery key and redirect to password reset.

- **Auth Required:** No
- **Content-Type:** `application/x-www-form-urlencoded`
- **CSRF:** Required
- **Rate Limit:** 2 per minute

**Request Parameters (form body):**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `recovery_key` | string | Yes | Recovery key in format `HARVEST-XXXX-XXXX-XXXX` |
| `csrf_token` | string | Yes | CSRF token from form |

**Success Response:** `302 Redirect` to `/reset-password?token=...`

**Error Response:** `400` with flashed message "Invalid recovery key"

```bash
curl -X POST https://himomstats.online/forgot-password \
  -d "recovery_key=HARVEST-ABCD-1234-WXYZ&csrf_token=TOKEN"
```

---

### GET /reset-password

Render the password reset form (requires valid reset token from session).

- **Auth Required:** No (requires valid reset token in session)
- **Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `token` | string | Yes | Reset token (valid for 10 minutes) |

- **Response:** HTML form for new password entry

```bash
curl "https://himomstats.online/reset-password?token=RESET_TOKEN"
```

---

### POST /reset-password

Set a new password after recovery key verification.

- **Auth Required:** No (requires valid reset token)
- **Content-Type:** `application/x-www-form-urlencoded`
- **CSRF:** Required
- **Rate Limit:** 5 per minute

**Request Parameters (form body):**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `token` | string | Yes | Reset token from URL |
| `new_password` | string | Yes | New password (min 6 characters) |
| `confirm_password` | string | Yes | Must match `new_password` |
| `csrf_token` | string | Yes | CSRF token from form |

**Success Response:** HTML page displaying new recovery key (save immediately)

**Error Response:** `400` with flashed error message

```bash
curl -X POST https://himomstats.online/reset-password \
  -d "token=RESET_TOKEN&new_password=newpass123&confirm_password=newpass123&csrf_token=TOKEN"
```

---

## BATCHES Endpoints

### GET /api/data

Get all active (non-archived) batches.

- **Auth Required:** API key or session
- **Response Type:** JSON array

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `include_history` | boolean | `false` | Include `rate_history` array per batch (omitted by default for performance) |

**Example Request:**

```bash
curl -H "X-API-Key: YOUR_KEY" \
  "https://himomstats.online/api/data"
```

**Example Response:**

```json
[
  {
    "id": "abc123-def456",
    "strain": "Blue Dream",
    "input_grams": 1000.0,
    "target_grams_each": 1.0,
    "stage": 2,
    "counts_0_5": 150,
    "counts_0_7": 100,
    "counts_1_0": 200,
    "planned_0_5": 300,
    "planned_0_7": 200,
    "planned_1_0": 400,
    "plan_use_grams": 800.0,
    "archived": 0,
    "display_order": 1,
    "production_start_time": "2026-02-25T08:00:00Z",
    "centrifuge_rpm": 2200,
    "centrifuge_time_seconds": 15,
    "centrifuge_cycles": 2,
    "centrifuge_fill_gauge_cycle1": 8.0,
    "centrifuge_fill_gauge_cycle2": 6.0,
    "cached_production_rate": 45.2,
    "testing_status": "none",
    "packaging_status": "available"
  }
]
```

**Error Response:**

```json
{
  "error": "An internal error occurred"
}
```
**Status:** `500`

---

### GET /api/archive

Get all archived batches.

- **Auth Required:** API key or session
- **Response Type:** JSON array (same structure as `/api/data`)

```bash
curl -H "X-API-Key: YOUR_KEY" \
  "https://himomstats.online/api/archive"
```

**Example Response:**

```json
[
  {
    "id": "xyz789-abc012",
    "strain": "OG Kush",
    "input_grams": 500.0,
    "stage": 7,
    "archived": 1,
    "counts_0_5": 400,
    "counts_0_7": 200,
    "counts_1_0": 150
  }
]
```

---

### GET /api/batches/last-updated

Polling endpoint that returns the timestamp of the most recent batch change. Use this to detect when to refresh batch data.

- **Auth Required:** API key or session
- **Response Type:** JSON object

```bash
curl -H "X-API-Key: YOUR_KEY" \
  "https://himomstats.online/api/batches/last-updated"
```

**Example Response:**

```json
{
  "timestamp": "2026-02-28T14:30:00.000Z"
}
```

---

### GET /api/batch/{batch_id}/rate-history

Get detailed production rate history for a specific batch.

- **Auth Required:** API key or session
- **URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `batch_id` | string | Yes | UUID of the batch |

```bash
curl -H "X-API-Key: YOUR_KEY" \
  "https://himomstats.online/api/batch/abc123-def456/rate-history"
```

**Example Response:**

```json
{
  "batch_id": "abc123-def456",
  "strain": "Blue Dream",
  "stage": 2,
  "rate_history": [
    {
      "timestamp": "2026-02-26T10:00:00Z",
      "rate": 42.5,
      "total_count": 100
    }
  ],
  "rate_metrics": {
    "average_rate": 44.0,
    "peak_rate": 52.1,
    "trend": "increasing"
  },
  "cached_production_rate": 45.2
}
```

**Error Response (404):**

```json
{
  "error": "Batch not found"
}
```

---

### GET /api/batch/{batch_id}/counts

This endpoint is handled via `GET /api/data` which includes counts for all batches. Individual batch counts are part of the batch object.

---

### POST /api/batch/{batch_id}/counts

Save production counts for a batch (auto-save endpoint).

- **Auth Required:** API key or session
- **Content-Type:** `application/json`
- **URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `batch_id` | string | Yes | UUID of the batch |

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `counts_0_5` | integer | No | Count of 0.5g pre-rolls produced |
| `counts_0_7` | integer | No | Count of 0.7g pre-rolls produced |
| `counts_1_0` | integer | No | Count of 1.0g pre-rolls produced |

```bash
curl -X POST -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"counts_0_5": 200, "counts_0_7": 150, "counts_1_0": 300}' \
  "https://himomstats.online/api/batch/abc123-def456/counts"
```

**Success Response:**

```json
{
  "ok": true
}
```

**Error Responses:**

```json
{"error": "Batch not found"}       // 404
{"error": "Invalid JSON"}          // 400
{"error": "Invalid value for counts_0_5"}  // 400
```

---

### POST /api/batch/{batch_id}/plan

Save planned counts for a batch. Values are automatically constrained by weight.

- **Auth Required:** API key or session
- **Content-Type:** `application/json`
- **URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `batch_id` | string | Yes | UUID of the batch |

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `planned_0_5` | integer | No | Planned 0.5g count |
| `planned_0_7` | integer | No | Planned 0.7g count |
| `planned_1_0` | integer | No | Planned 1.0g count |
| `plan_use_grams` | float | No | Grams allocated for this plan (0 = use all input_grams) |

```bash
curl -X POST -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"planned_0_5": 400, "planned_0_7": 200, "planned_1_0": 300, "plan_use_grams": 800}' \
  "https://himomstats.online/api/batch/abc123-def456/plan"
```

**Success Response:**

```json
{
  "ok": true,
  "adjusted": false,
  "planned_0_5": 400,
  "planned_0_7": 200,
  "planned_1_0": 300
}
```

If weight constraints required adjustment, `adjusted` will be `true` and the returned values will differ from the input.

---

### GET /api/strain/{strain_name}/rate-projection

Get projected production rate for a strain based on historical data.

- **Auth Required:** API key or session
- **URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `strain_name` | string | Yes | Name of the strain |

```bash
curl -H "X-API-Key: YOUR_KEY" \
  "https://himomstats.online/api/strain/Blue%20Dream/rate-projection"
```

**Example Response (with data):**

```json
{
  "strain_name": "Blue Dream",
  "has_data": true,
  "projected_rate": 48.5,
  "confidence": 0.85,
  "sample_size": 4,
  "historical_rates": [42.0, 45.5, 48.2, 52.1]
}
```

**Example Response (no data):**

```json
{
  "strain_name": "New Strain",
  "has_data": false,
  "message": "No historical rate data available for this strain"
}
```

---

### POST /api/archive/{batch_id}

Toggle archive status of a batch.

- **Auth Required:** API key or session
- **Content-Type:** `application/json`
- **URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `batch_id` | string | Yes | UUID of the batch |

**Request Body (optional):**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `archive` | boolean | `true` | `true` to archive, `false` to unarchive |

```bash
curl -X POST -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"archive": true}' \
  "https://himomstats.online/api/archive/abc123-def456"
```

**Success Response:**

```json
{
  "status": "success",
  "action": "archived"
}
```

**Error Response (404):**

```json
{
  "error": "Batch not found or already in requested state"
}
```

---

### POST /api/public/archive/{batch_id}

Archive a completed batch (stage 7 / "Done" only). More restrictive than `/api/archive/{batch_id}`.

- **Auth Required:** API key or session
- **URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `batch_id` | string | Yes | UUID of the batch |

```bash
curl -X POST -H "X-API-Key: YOUR_KEY" \
  "https://himomstats.online/api/public/archive/abc123-def456"
```

**Success Response:**

```json
{
  "status": "success",
  "action": "archived"
}
```

**Error Responses:**

```json
{"error": "Batch not found"}                                      // 404
{"error": "Only completed batches (Done stage) can be archived"}  // 403
{"error": "Batch is already archived"}                             // 400
```

---

### GET /api/allocation-preview

Preview how a given weight would be allocated across sizes using current allocation settings.

- **Auth Required:** Session only
- **Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `weight` | float | `1000` | Total grams to allocate |

```bash
curl -b session_cookie \
  "https://himomstats.online/api/allocation-preview?weight=1000"
```

**Example Response:**

```json
{
  "allocation": [40, 30, 30],
  "counts_0_5": 800,
  "counts_0_7": 428,
  "counts_1_0": 300,
  "total_units": 1528,
  "expected_output": 980.0
}
```

---

### POST /api/reorder

Reorder batches by providing a sorted array of batch IDs.

- **Auth Required:** API key or session
- **Content-Type:** `application/json`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `batch_ids` | array of strings | Yes | Ordered list of batch UUIDs |

```bash
curl -X POST -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"batch_ids": ["id1", "id2", "id3"]}' \
  "https://himomstats.online/api/reorder"
```

**Success Response:**

```json
{
  "status": "success"
}
```

**Error Response (400):**

```json
{
  "error": "No batch IDs provided"
}
```

---

## INVENTORY Endpoints

### GET /api/inventory/

Get current paper/cone inventory data for all sizes.

- **Auth Required:** API key or session
- **Response Type:** JSON object

```bash
curl -H "X-API-Key: YOUR_KEY" \
  "https://himomstats.online/api/inventory/"
```

**Example Response:**

```json
{
  "inventory": {
    "current_boxes": {
      "0_5": 10,
      "0_7": 8,
      "1_0": 12
    },
    "papers_per_box": {
      "0_5": 1000,
      "0_7": 900,
      "1_0": 1000
    },
    "alert_thresholds": {
      "0_5": 5,
      "0_7": 5,
      "1_0": 5
    }
  },
  "current_papers": {
    "0_5": 10000,
    "0_7": 7200,
    "1_0": 12000
  },
  "alerts": [],
  "analytics": {
    "predicted_days_remaining": {
      "0_5": 45.2,
      "0_7": 30.1,
      "1_0": 55.8
    }
  }
}
```

---

### POST /api/inventory/update

Update inventory counts for a specific size.

- **Auth Required:** API key or session
- **Content-Type:** `application/json`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `size` | string | Yes | Size key: `"0_5"`, `"0_7"`, or `"1_0"` |
| `box_count` | integer | No | Number of boxes |
| `individual_papers` | integer | No | Loose individual papers |

```bash
curl -X POST -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"size": "0_5", "box_count": 15, "individual_papers": 250}' \
  "https://himomstats.online/api/inventory/update"
```

**Success Response:**

```json
{
  "status": "success",
  "message": "Updated 0.5g inventory to 15 boxes, 250 individual papers",
  "inventory": {
    "boxes": 15,
    "individual_papers": 250,
    "total_papers": 15250
  }
}
```

**Error Response (400):**

```json
{
  "error": "Invalid size"
}
```

---

### POST /api/inventory/settings

Update inventory settings (thresholds and papers-per-box).

- **Auth Required:** API key or session
- **Content-Type:** `application/json`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `thresholds` | object | No | Low-stock alert thresholds per size |
| `thresholds.0_5` | integer | No | Threshold for 0.5g (default: 5) |
| `thresholds.0_7` | integer | No | Threshold for 0.7g (default: 5) |
| `thresholds.1_0` | integer | No | Threshold for 1.0g (default: 5) |
| `papers_per_box` | object | No | Papers per box configuration |
| `papers_per_box.0_5` | integer | No | Papers per box for 0.5g (default: 1000) |
| `papers_per_box.0_7` | integer | No | Papers per box for 0.7g (default: 800) |
| `papers_per_box.1_0` | integer | No | Papers per box for 1.0g (default: 800) |

```bash
curl -X POST -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"thresholds": {"0_5": 3, "0_7": 3, "1_0": 3}}' \
  "https://himomstats.online/api/inventory/settings"
```

**Success Response:**

```json
{
  "status": "success",
  "message": "Inventory settings updated"
}
```

---

## FINISHED GOODS Endpoints

### GET /api/finished-goods/

List all finished goods packages with optional filtering.

- **Auth Required:** API key or session
- **Response Type:** JSON object

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `include_archived` | boolean | `false` | Include archived packages |
| `strain` | string | | Filter by strain name (partial match) |
| `status` | string | | Filter by status: `active`, `depleted`, `archived` |
| `search` | string | | Search by METRC number or strain name |

```bash
curl -H "X-API-Key: YOUR_KEY" \
  "https://himomstats.online/api/finished-goods/?status=active&search=Blue"
```

**Example Response:**

```json
{
  "packages": [
    {
      "metrc_number": "1A406030000B1E2000014149",
      "strain": "Blue Dream",
      "initial_grams": 500.0,
      "current_grams": 350.2,
      "status": "active",
      "created_date": "2026-02-20T10:00:00Z",
      "updated_date": "2026-02-28T14:30:00Z",
      "notes": "Batch from Feb 2026",
      "source_batch_id": "abc123-def456",
      "grams_ordered": 100.0,
      "grams_packed": 80.0,
      "wholesale_holds": {}
    }
  ],
  "total": 1,
  "summary": {
    "total_packages": 15,
    "active_packages": 12,
    "total_grams": 5200.5,
    "total_strains": 8
  },
  "settings": {}
}
```

---

### GET /api/finished-goods/last-updated

Polling endpoint for finished goods changes.

- **Auth Required:** API key or session

```bash
curl -H "X-API-Key: YOUR_KEY" \
  "https://himomstats.online/api/finished-goods/last-updated"
```

**Example Response:**

```json
{
  "timestamp": "2026-02-28T14:30:00.000Z"
}
```

---

### GET /api/finished-goods/summary

Get summary statistics for finished goods inventory.

- **Auth Required:** API key or session

```bash
curl -H "X-API-Key: YOUR_KEY" \
  "https://himomstats.online/api/finished-goods/summary"
```

**Example Response:**

```json
{
  "total_packages": 15,
  "active_packages": 12,
  "depleted_packages": 2,
  "archived_packages": 1,
  "total_grams": 5200.5,
  "total_strains": 8
}
```

---

### GET /api/finished-goods/history

Get recent change history across all packages.

- **Auth Required:** API key or session

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | `100` | Maximum number of history entries to return |

```bash
curl -H "X-API-Key: YOUR_KEY" \
  "https://himomstats.online/api/finished-goods/history?limit=50"
```

**Example Response:**

```json
{
  "history": [
    {
      "metrc_number": "1A406030000B1E2000014149",
      "timestamp": "2026-02-28T14:00:00Z",
      "change_type": "deduct",
      "current_grams": 350.2,
      "grams_ordered": 100.0,
      "grams_packed": 80.0,
      "status": "active",
      "details": "{\"reason\": \"wholesale order\"}"
    }
  ],
  "total": 1
}
```

---

### GET /api/finished-goods/calculator

Calculate pre-roll unit estimates for a given number of grams.

- **Auth Required:** API key or session

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `grams` | float | Yes | Input grams to calculate |

```bash
curl -H "X-API-Key: YOUR_KEY" \
  "https://himomstats.online/api/finished-goods/calculator?grams=500"
```

**Example Response:**

```json
{
  "input_grams": 500.0,
  "primary_sizes": {
    "0.5g_singles": 1000,
    "1.0g_singles": 500,
    "0.5g_6pack": 166,
    "0.5g_12pack": 83
  },
  "custom_sizes": {
    "0.7g": 714,
    "0.8g": 625
  }
}
```

**Error Response (400):**

```json
{
  "error": "grams parameter is required"
}
```

---

### GET /api/finished-goods/{metrc_number}

Get a specific package by METRC number.

- **Auth Required:** API key or session
- **URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `metrc_number` | string | Yes | METRC package number |

```bash
curl -H "X-API-Key: YOUR_KEY" \
  "https://himomstats.online/api/finished-goods/1A406030000B1E2000014149"
```

**Example Response:**

```json
{
  "metrc_number": "1A406030000B1E2000014149",
  "strain": "Blue Dream",
  "initial_grams": 500.0,
  "current_grams": 350.2,
  "status": "active",
  "created_date": "2026-02-20T10:00:00Z",
  "updated_date": "2026-02-28T14:30:00Z",
  "notes": "",
  "source_batch_id": "abc123-def456",
  "grams_ordered": 100.0,
  "grams_packed": 80.0,
  "grams_fulfilled": 75.0,
  "sku_breakdown": null,
  "apex_auto_inventory": 0
}
```

**Error Response (404):**

```json
{
  "error": "Package not found"
}
```

---

### POST /api/finished-goods/

Add a new finished goods package.

- **Auth Required:** API key or session
- **Content-Type:** `application/json`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `metrc_number` | string | Yes | Unique METRC package number |
| `strain` | string | Yes | Strain name |
| `grams` | float | Yes | Initial grams (must be positive) |
| `notes` | string | No | Optional notes |
| `source_batch_id` | string | No | Reference to the source production batch |

```bash
curl -X POST -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"metrc_number": "1A406030000B1E2000099999", "strain": "OG Kush", "grams": 750}' \
  "https://himomstats.online/api/finished-goods/"
```

**Success Response (201):**

```json
{
  "success": true,
  "message": "Package 1A406030000B1E2000099999 created successfully",
  "package": {
    "metrc_number": "1A406030000B1E2000099999",
    "strain": "OG Kush",
    "initial_grams": 750.0,
    "current_grams": 750.0,
    "status": "active"
  }
}
```

**Error Responses:**

```json
{"error": "metrc_number is required"}     // 400
{"error": "strain is required"}           // 400
{"error": "grams must be a positive number"}  // 400
```

---

### PUT /api/finished-goods/{metrc_number}

Update editable fields of a package.

- **Auth Required:** API key or session
- **Content-Type:** `application/json`

**Request Body (all optional):**

| Field | Type | Description |
|-------|------|-------------|
| `strain` | string | Update strain name |
| `notes` | string | Update notes |
| `source_batch_id` | string | Link to source batch |
| `reason` | string | Audit note for the change |

```bash
curl -X PUT -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Updated notes", "reason": "Correction"}' \
  "https://himomstats.online/api/finished-goods/1A406030000B1E2000014149"
```

**Success Response:**

```json
{
  "success": true,
  "updated_fields": ["notes"],
  "package": {
    "metrc_number": "1A406030000B1E2000014149",
    "strain": "Blue Dream",
    "notes": "Updated notes"
  }
}
```

---

### DELETE /api/finished-goods/{metrc_number}

Delete a finished goods package. *(Note: This endpoint may archive rather than permanently delete depending on implementation.)*

- **Auth Required:** API key or session

```bash
curl -X DELETE -H "X-API-Key: YOUR_KEY" \
  "https://himomstats.online/api/finished-goods/1A406030000B1E2000014149"
```

---

## WHOLESALE Endpoints

### GET /api/wholesale/inventory

Get wholesale-friendly inventory data grouped by strain.

- **Auth Required:** Session only

```bash
curl -b session_cookie \
  "https://himomstats.online/api/wholesale/inventory"
```

**Example Response:**

```json
{
  "success": true,
  "strains": [
    {
      "strain": "Blue Dream",
      "packages": [
        {
          "metrc_number": "1A406030000B1E2000014149",
          "available_grams": 350.2,
          "skus": {
            "0.5g Singles": {"units": 700, "available": 650},
            "1.0g Singles": {"units": 350, "available": 320}
          }
        }
      ]
    }
  ]
}
```

---

### POST /api/wholesale/hold

Create an inventory hold (reservation) for wholesale.

- **Auth Required:** Session only
- **Content-Type:** `application/json`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `metrc_number` | string | Yes | Package METRC number |
| `sku_name` | string | Yes | SKU name (e.g., "0.5g Singles") |
| `quantity` | integer | Yes | Number of units to hold (must be positive) |
| `notes` | string | No | Optional notes for the hold |

```bash
curl -X POST -b session_cookie \
  -H "Content-Type: application/json" \
  -d '{"metrc_number": "1A406030000B1E2000014149", "sku_name": "0.5g Singles", "quantity": 100, "notes": "Wholesale order #456"}' \
  "https://himomstats.online/api/wholesale/hold"
```

**Success Response:**

```json
{
  "success": true,
  "hold_id": "hold-abc123",
  "message": "Hold created"
}
```

**Error Responses:**

```json
{"error": "metrc_number, sku_name, and quantity are required"}  // 400
{"error": "Quantity must be positive"}                           // 400
{"error": "Only 650 units available (requested 700)"}           // 400
```

---

### DELETE /api/wholesale/hold/{hold_id}

Release (delete) an inventory hold.

- **Auth Required:** Session only
- **URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `hold_id` | string | Yes | UUID of the hold |

```bash
curl -X DELETE -b session_cookie \
  "https://himomstats.online/api/wholesale/hold/hold-abc123"
```

**Success Response:**

```json
{
  "success": true,
  "message": "Hold released"
}
```

**Error Response (404):**

```json
{
  "success": false,
  "error": "Hold not found"
}
```

---

### GET /api/wholesale/holds

List all active holds. Optionally filter by METRC number.

- **Auth Required:** Session only

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `metrc_number` | string | No | Filter holds for a specific package |

```bash
curl -b session_cookie \
  "https://himomstats.online/api/wholesale/holds?metrc_number=1A406030000B1E2000014149"
```

**Example Response:**

```json
{
  "success": true,
  "holds": [
    {
      "id": "hold-abc123",
      "metrc_number": "1A406030000B1E2000014149",
      "sku_name": "0.5g Singles",
      "quantity": 100,
      "created_date": "2026-02-28T10:00:00Z",
      "notes": "Wholesale order #456"
    }
  ]
}
```

---

### GET /api/wholesale/last-updated

Polling endpoint returning a composite fingerprint of wholesale data changes.

- **Auth Required:** Session only

```bash
curl -b session_cookie \
  "https://himomstats.online/api/wholesale/last-updated"
```

**Example Response:**

```json
{
  "fingerprint": "2026-02-28T14:30:00Z|2026-02-28T12:00:00Z|5"
}
```

The fingerprint combines: latest hold timestamp, latest finished goods history timestamp, and hold count.

---

## CENTRIFUGE Endpoints

All centrifuge endpoints are prefixed with `/api/centrifuge`.

### POST /api/centrifuge/calculate

Calculate centrifugal force (G-force) for given RPM and machine type.

- **Auth Required:** API key or session
- **Content-Type:** `application/json`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `rpm` | integer | Yes | Revolutions per minute (must be > 0) |
| `centrifuge_type` | string | No | Machine type: `"silver_bullet"` (default) or `"lab_geek"` |

```bash
curl -X POST -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"rpm": 2200, "centrifuge_type": "silver_bullet"}' \
  "https://himomstats.online/api/centrifuge/calculate"
```

**Example Response:**

```json
{
  "success": true,
  "rpm": 2200,
  "centrifuge_type": "silver_bullet",
  "g_force": 228.5,
  "radius_inches": 4.125,
  "safety_zone": "optimal"
}
```

---

### POST /api/centrifuge/compare

Compare centrifuge settings across machines to find equivalent settings.

- **Auth Required:** API key or session
- **Content-Type:** `application/json`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `rpm` | integer | Yes | Source RPM (must be > 0) |
| `source_centrifuge` | string | No | Source machine type (default: `"silver_bullet"`) |

```bash
curl -X POST -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"rpm": 2200, "source_centrifuge": "silver_bullet"}' \
  "https://himomstats.online/api/centrifuge/compare"
```

**Example Response:**

```json
{
  "success": true,
  "source": {
    "centrifuge": "silver_bullet",
    "rpm": 2200,
    "g_force": 228.5
  },
  "equivalent": {
    "lab_geek": {
      "rpm": 2000,
      "g_force": 228.3
    }
  }
}
```

---

### GET /api/centrifuge/curve-data

Get force curve data points for graphing.

- **Auth Required:** API key or session

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `centrifuge` | string | `"silver_bullet"` | Machine type |
| `rpm_min` | integer | `500` | Minimum RPM |
| `rpm_max` | integer | `5000` | Maximum RPM |
| `step` | integer | `100` | RPM step between data points |

```bash
curl -H "X-API-Key: YOUR_KEY" \
  "https://himomstats.online/api/centrifuge/curve-data?centrifuge=silver_bullet&rpm_min=500&rpm_max=3000&step=100"
```

**Example Response:**

```json
{
  "success": true,
  "centrifuge": "silver_bullet",
  "data": [
    {"rpm": 500, "g_force": 11.8},
    {"rpm": 600, "g_force": 17.0},
    {"rpm": 700, "g_force": 23.1}
  ]
}
```

---

### GET /api/centrifuge/settings-guide

Get recommended centrifuge settings and safety zone information.

- **Auth Required:** API key or session

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `material` | string | `"standard"` | Material type for recommendations |

```bash
curl -H "X-API-Key: YOUR_KEY" \
  "https://himomstats.online/api/centrifuge/settings-guide?material=standard"
```

**Example Response:**

```json
{
  "success": true,
  "recommendations": {
    "standard": {
      "rpm_range": [1800, 2500],
      "time_range": [10, 20],
      "cycles": 2
    }
  },
  "safety_zones": {
    "safe": {"max_rpm": 3000},
    "caution": {"max_rpm": 4000},
    "danger": {"max_rpm": 5000}
  },
  "centrifuges": {
    "silver_bullet": {
      "name": "Silver Bullet",
      "radius_inches": 4.125,
      "max_rpm": 5000,
      "min_rpm": 500
    },
    "lab_geek": {
      "name": "Lab Geek",
      "radius_inches": 5.0,
      "max_rpm": 4500,
      "min_rpm": 500
    }
  }
}
```

---

### POST /api/centrifuge/impulse-calculate

Calculate impulse-based centrifuge metrics factoring in time and weight.

- **Auth Required:** API key or session
- **Content-Type:** `application/json`

**Request Body:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `rpm` | integer | Yes | | RPM (must be > 0) |
| `time_seconds` | float | No | `15.0` | Duration in seconds |
| `weight_grams` | float | No | `1.0` | Pre-roll weight in grams |
| `centrifuge_type` | string | No | `"silver_bullet"` | Machine type |

```bash
curl -X POST -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"rpm": 2200, "time_seconds": 15, "weight_grams": 1.0, "centrifuge_type": "silver_bullet"}' \
  "https://himomstats.online/api/centrifuge/impulse-calculate"
```

**Example Response:**

```json
{
  "success": true,
  "data": {
    "g_force": 228.5,
    "impulse_newton_seconds": 33.6,
    "impulse_zone": "optimal",
    "impulse_zones": {
      "light": {"impulse_min": 0, "impulse_max": 15},
      "moderate": {"impulse_min": 15, "impulse_max": 30},
      "optimal": {"impulse_min": 30, "impulse_max": 45},
      "heavy": {"impulse_min": 45, "impulse_max": 100}
    }
  }
}
```

---

### POST /api/centrifuge/target-match

Find RPM or time settings to match a target impulse value.

- **Auth Required:** API key or session
- **Content-Type:** `application/json`

**Request Body:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `target_impulse` | float | No | System default | Target impulse in Newton-seconds |
| `adjust_mode` | string | No | `"rpm"` | `"rpm"` or `"time"` -- which to adjust |
| `rpm` | integer | No | `2200` | Current/fixed RPM |
| `time_seconds` | float | No | `15.0` | Current/fixed time |
| `weight_grams` | float | No | `1.0` | Pre-roll weight |
| `centrifuge_type` | string | No | `"silver_bullet"` | Machine type |

```bash
curl -X POST -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"target_impulse": 35.0, "adjust_mode": "rpm", "time_seconds": 15, "weight_grams": 1.0}' \
  "https://himomstats.online/api/centrifuge/target-match"
```

**Example Response:**

```json
{
  "success": true,
  "data": {
    "target_impulse": 35.0,
    "adjust_mode": "rpm",
    "recommended_rpm": 2350,
    "time_seconds": 15.0,
    "achieved_impulse": 35.2,
    "g_force": 260.8
  }
}
```

---

### GET /api/centrifuge/trends/{strain}

*(Also available as `/api/centrifuge-trends/{strain_name}`)*

Get temporal/trend-based centrifuge recommendations for a strain.

- **Auth Required:** API key or session
- **URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `strain` | string | Yes | Strain name |

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `grind_size` | string | No | Filter: `"fine"`, `"medium"`, `"coarse"` |
| `target_batch` | integer | No | Target batch number for projections |
| `days_since_harvest` | integer | No | Days since harvest for moisture drift compensation |

```bash
curl -H "X-API-Key: YOUR_KEY" \
  "https://himomstats.online/api/centrifuge-trends/Blue%20Dream?grind_size=medium"
```

**Example Response:**

```json
{
  "strain": "Blue Dream",
  "has_data": true,
  "timeline": [
    {
      "batch_number": 1,
      "rpm": 2000,
      "time_seconds": 15,
      "fill_gauge": 8,
      "yield_percent": 94.2
    }
  ],
  "trend_analysis": {
    "rpm_trend": "increasing",
    "optimal_rpm": 2200
  },
  "recommendation": {
    "rpm": 2250,
    "time_seconds": 15,
    "fill_gauge_cycle1": 7,
    "confidence": 0.82
  }
}
```

---

## SNAPSHOTS Endpoints

All snapshot endpoints are prefixed with `/api/snapshots`.

### GET /api/snapshots/history

Get list of available inventory recommendation snapshots.

- **Auth Required:** Session only

```bash
curl -b session_cookie \
  "https://himomstats.online/api/snapshots/history"
```

**Example Response:**

```json
{
  "snapshots": [
    {
      "timestamp": "2026-02-28T10:00:00Z",
      "files_processed": ["store1.csv", "store2.csv"],
      "strain_count": 15
    }
  ]
}
```

---

### GET /api/snapshots/{timestamp}

Get a specific snapshot by its timestamp.

- **Auth Required:** Session only
- **URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `timestamp` | string | Yes | ISO 8601 timestamp of the snapshot |

```bash
curl -b session_cookie \
  "https://himomstats.online/api/snapshots/2026-02-28T10:00:00Z"
```

**Example Response:**

```json
{
  "timestamp": "2026-02-28T10:00:00Z",
  "data": {
    "combined": [
      {
        "strain": "Blue Dream",
        "total_inventory": 450,
        "avg_sold_per_day": 12.5,
        "days_until_stockout": 36,
        "urgency": "low",
        "priority_score": 25
      }
    ],
    "stores": ["Store A", "Store B"]
  }
}
```

**Error Response (404):**

```json
{
  "error": "Snapshot not found"
}
```

---

### POST /api/snapshots/compare-detailed

Compare two snapshots with detailed metrics.

- **Auth Required:** Session only
- **Content-Type:** `application/json`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timestamp1` | string | Yes | First snapshot timestamp |
| `timestamp2` | string | Yes | Second snapshot timestamp |
| `store_filter` | string | No | Filter comparison to a specific store |

```bash
curl -X POST -b session_cookie \
  -H "Content-Type: application/json" \
  -d '{"timestamp1": "2026-02-20T10:00:00Z", "timestamp2": "2026-02-28T10:00:00Z"}' \
  "https://himomstats.online/api/snapshots/compare-detailed"
```

**Example Response:**

```json
{
  "comparisons": [
    {
      "strain": "Blue Dream",
      "status": "updated",
      "old": {"total_inventory": 600, "urgency": "low"},
      "new": {"total_inventory": 450, "urgency": "medium"},
      "changes": {"inventory_delta": -150}
    }
  ]
}
```

---

### POST /api/snapshots/insights

Generate insights from comparing two snapshots.

- **Auth Required:** Session only
- **Content-Type:** `application/json`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timestamp1` | string | Yes | First snapshot timestamp |
| `timestamp2` | string | Yes | Second snapshot timestamp |

```bash
curl -X POST -b session_cookie \
  -H "Content-Type: application/json" \
  -d '{"timestamp1": "2026-02-20T10:00:00Z", "timestamp2": "2026-02-28T10:00:00Z"}' \
  "https://himomstats.online/api/snapshots/insights"
```

**Example Response:**

```json
{
  "insights": [
    {
      "type": "danger",
      "title": "Urgency Increased",
      "message": "3 strain(s) now more urgent: Blue Dream, OG Kush, Gelato"
    },
    {
      "type": "info",
      "title": "New Strains",
      "message": "2 new strain(s) appeared: Wedding Cake, Runtz"
    }
  ]
}
```

---

## MISC Endpoints

### GET /api/version

Get the running application version. **Public endpoint -- no authentication required.**

```bash
curl "https://himomstats.online/api/version"
```

**Example Response:**

```json
{
  "version": "2.0.0"
}
```

---

### GET /api/backup-status

Get backup system health status.

- **Auth Required:** API key or session

```bash
curl -H "X-API-Key: YOUR_KEY" \
  "https://himomstats.online/api/backup-status"
```

**Example Response:**

```json
{
  "last_backup": "2026-02-28T06:00:00Z",
  "backup_count": 45,
  "backup_size_mb": 12.5,
  "status": "healthy",
  "next_scheduled": "2026-02-29T06:00:00Z"
}
```

---

### GET /api/settings

Get current application settings.

- **Auth Required:** API key or session

```bash
curl -H "X-API-Key: YOUR_KEY" \
  "https://himomstats.online/api/settings"
```

**Example Response:**

```json
{
  "allocation": [40, 30, 30],
  "tare_weights": {
    "0_5": 0.12,
    "0_7": 0.15,
    "1_0": 0.18
  },
  "test_alert_hours": 48,
  "work_schedule": {
    "start_hour": 8,
    "end_hour": 17,
    "work_days": [0, 1, 2, 3, 4]
  }
}
```

---

### GET /api/api-key

View the current API key. Only accessible via web session (not API key auth).

- **Auth Required:** Session only

```bash
curl -b session_cookie \
  "https://himomstats.online/api/api-key"
```

**Example Response:**

```json
{
  "api_key": "abc123def456ghi789",
  "usage": {
    "header": "X-API-Key",
    "example": "curl -H \"X-API-Key: YOUR_KEY\" http://server/api/data"
  }
}
```

---

### POST /api/api-key/regenerate

Generate a new API key, invalidating the old one.

- **Auth Required:** Session only

```bash
curl -X POST -b session_cookie \
  "https://himomstats.online/api/api-key/regenerate"
```

**Example Response:**

```json
{
  "api_key": "new_key_xyz789abc012",
  "message": "API key regenerated. Old key is now invalid."
}
```

---

### GET /api/overview

Get production overview with stage counts and priority alerts.

- **Auth Required:** API key or session

```bash
curl -H "X-API-Key: YOUR_KEY" \
  "https://himomstats.online/api/overview"
```

**Example Response:**

```json
{
  "stage_counts": {
    "Not ground": 2,
    "Ground": 1,
    "In progress": 3,
    "Finished": 0,
    "Waiting on testing": 1,
    "Test passed": 0,
    "Bagging": 1,
    "Done": 2
  },
  "production_stats": {
    "today_total": 450,
    "today_0_5": 200,
    "today_0_7": 100,
    "today_1_0": 150
  },
  "priority_batches": [
    {
      "strain": "OG Kush",
      "stage": "In progress",
      "days_in_stage": 3
    }
  ],
  "total_active": 10
}
```

---

### GET /api/audit

Get the full audit trail data.

- **Auth Required:** API key or session

```bash
curl -H "X-API-Key: YOUR_KEY" \
  "https://himomstats.online/api/audit"
```

**Example Response:**

```json
[
  {
    "batch": "abc123-def456",
    "strain": "Blue Dream",
    "ts": "2026-02-28T14:30:00Z",
    "field": "stage",
    "old": 1,
    "new": 2
  }
]
```

---

### GET /api/production-history

Get historical production data over a number of days.

- **Auth Required:** API key or session

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | `7` | Number of days of history (1-90) |

```bash
curl -H "X-API-Key: YOUR_KEY" \
  "https://himomstats.online/api/production-history?days=30"
```

**Example Response:**

```json
{
  "days": 30,
  "daily_production": [
    {
      "date": "2026-02-28",
      "total": 450,
      "0_5": 200,
      "0_7": 100,
      "1_0": 150
    }
  ]
}
```

---

### POST /api/dismiss-inventory-alert/{size}

Dismiss a low-stock inventory alert for a specific size.

- **Auth Required:** Session only
- **URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `size` | string | Yes | Size key: `"0_5"`, `"0_7"`, or `"1_0"` |

```bash
curl -X POST -b session_cookie \
  "https://himomstats.online/api/dismiss-inventory-alert/0_5"
```

**Success Response:**

```json
{
  "status": "success",
  "message": "Alert for 0_5 dismissed"
}
```

---

### POST /api/dismiss-inventory-alerts

Dismiss all inventory alerts at once.

- **Auth Required:** Session only

```bash
curl -X POST -b session_cookie \
  "https://himomstats.online/api/dismiss-inventory-alerts"
```

**Success Response:**

```json
{
  "status": "success",
  "message": "All inventory alerts dismissed"
}
```

---

### GET /api/apex-sync-status

Get the timestamp of the last ApexAPI sync request.

- **Auth Required:** API key or session

```bash
curl -H "X-API-Key: YOUR_KEY" \
  "https://himomstats.online/api/apex-sync-status"
```

**Example Response:**

```json
{
  "last_sync_requested": "2026-02-28T14:00:00Z"
}
```

---

### POST /api/apex-sync-trigger

Manually trigger an ApexAPI sync by updating the sync timestamp.

- **Auth Required:** API key or session

```bash
curl -X POST -H "X-API-Key: YOUR_KEY" \
  "https://himomstats.online/api/apex-sync-trigger"
```

**Success Response:**

```json
{
  "success": true,
  "last_sync_requested": "2026-02-28T15:30:00Z"
}
```

---

### GET /api/pushover/settings

Get Pushover notification configuration.

- **Auth Required:** Session only

```bash
curl -b session_cookie \
  "https://himomstats.online/api/pushover/settings"
```

**Example Response:**

```json
{
  "enabled": true,
  "user_key": "u****key",
  "warning_grams": 500,
  "critical_grams": 100,
  "cooldown_hours": 24,
  "has_user_key": true
}
```

---

### PUT /api/pushover/settings

Update Pushover notification configuration.

- **Auth Required:** Session only
- **Content-Type:** `application/json`

**Request Body (all optional):**

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | boolean | Enable/disable notifications |
| `user_key` | string | Pushover user key |
| `warning_grams` | float | Grams threshold for warning alerts |
| `critical_grams` | float | Grams threshold for critical alerts |
| `cooldown_hours` | integer | Hours between repeat alerts (min: 1) |

```bash
curl -X PUT -b session_cookie \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "warning_grams": 400, "critical_grams": 50}' \
  "https://himomstats.online/api/pushover/settings"
```

**Success Response:**

```json
{
  "success": true,
  "message": "Pushover settings updated",
  "settings": {
    "enabled": true,
    "warning_grams": 400.0,
    "critical_grams": 50.0,
    "cooldown_hours": 24
  }
}
```

---

### POST /api/pushover/test

Send a test Pushover notification.

- **Auth Required:** Session only

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `level` | string | `"warning"` | Alert level for the test |

```bash
curl -X POST -b session_cookie \
  "https://himomstats.online/api/pushover/test?level=critical"
```

**Success Response:**

```json
{
  "success": true,
  "message": "Test critical notification sent successfully!"
}
```

**Error Response (400):**

```json
{
  "success": false,
  "error": "No user key configured"
}
```

---

### GET /api/centrifuge-trends/{strain_name}

Get temporal/trend-based centrifuge recommendations for a strain.

- **Auth Required:** API key or session
- See [GET /api/centrifuge/trends/{strain}](#get-apicentrifugetrendsstrain) for full documentation. This is an alias endpoint at the top-level path.

---

### GET /api/centrifuge-recommendations-unified/{strain_name}

Get unified centrifuge setting recommendations with per-size data.

- **Auth Required:** API key or session
- **URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `strain_name` | string | Yes | Strain name |

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `grind_size` | string | | Filter: `"fine"`, `"medium"`, `"coarse"` |
| `priority_mode` | string | `"weight"` | Optimization: `"weight"` or `"count"` |
| `temporal` | string | `"false"` | Set to `"true"` for trend-based adjustments |
| `target_batch` | integer | | Target batch number (temporal mode) |
| `days_since_harvest` | integer | | Days since harvest (temporal mode) |

```bash
curl -H "X-API-Key: YOUR_KEY" \
  "https://himomstats.online/api/centrifuge-recommendations-unified/Blue%20Dream?priority_mode=weight"
```

---

### POST /api/fill-gauge-log

Log fill gauge readings. *(Note: This endpoint was not found in the current codebase blueprints. It may be handled inline in another view or be a planned endpoint.)*

---

## PWA Endpoints

These endpoints support Progressive Web App functionality. No authentication required.

### GET /manifest.json

PWA manifest file.

- **Cache:** 24 hours
- **Content-Type:** `application/json`

```bash
curl "https://himomstats.online/manifest.json"
```

---

### GET /sw.js

Service worker script.

- **Cache:** No cache (max-age=0)
- **Content-Type:** `application/javascript`

```bash
curl "https://himomstats.online/sw.js"
```

---

### GET /icon-192.png

192x192 app icon (served as SVG).

- **Cache:** 24 hours

```bash
curl "https://himomstats.online/icon-192.png"
```

---

### GET /icon-512.png

512x512 app icon (served as SVG).

- **Cache:** 24 hours

```bash
curl "https://himomstats.online/icon-512.png"
```

---

### GET /favicon.ico

Favicon (served as SVG).

- **Cache:** 24 hours

```bash
curl "https://himomstats.online/favicon.ico"
```

---

## Additional API Endpoints Discovered in Source

The following additional endpoints were found in the codebase:

### POST /api/batch/{batch_id}/centrifuge

Save centrifuge settings for a batch from the plan page.

- **Auth Required:** Session only
- **Content-Type:** `application/json`

**Request Body (all optional):**

| Field | Type | Description |
|-------|------|-------------|
| `centrifuge_rpm` | integer | RPM setting |
| `centrifuge_time_seconds` | integer | Duration in seconds |
| `centrifuge_cycles` | integer | Number of cycles |
| `centrifuge_fill_gauge_cycle1` | integer | Fill gauge reading for cycle 1 |
| `centrifuge_fill_gauge_cycle2` | integer | Fill gauge reading for cycle 2 |

```bash
curl -X POST -b session_cookie \
  -H "Content-Type: application/json" \
  -d '{"centrifuge_rpm": 2200, "centrifuge_time_seconds": 15, "centrifuge_cycles": 2}' \
  "https://himomstats.online/api/batch/abc123-def456/centrifuge"
```

---

### POST /api/update-progress/{batch_id}

Update production progress without page reload.

- **Auth Required:** API key or session
- **Content-Type:** `application/json`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `counts_0_5` | integer | Yes | Current 0.5g count |
| `counts_0_7` | integer | Yes | Current 0.7g count |
| `counts_1_0` | integer | Yes | Current 1.0g count |

**Success Response:**

```json
{
  "status": "success",
  "message": "Production progress updated successfully!",
  "data": {
    "counts_0_5": 200,
    "counts_0_7": 150,
    "counts_1_0": 300,
    "planned_0_5": 400,
    "planned_0_7": 200,
    "planned_1_0": 400,
    "total_actual": 650,
    "total_planned": 1000,
    "progress_0_5": 50.0,
    "progress_0_7": 75.0,
    "progress_1_0": 75.0,
    "overall_progress": 65.0,
    "today_0_5": 50,
    "today_0_7": 30,
    "today_1_0": 40,
    "today_total": 120
  }
}
```

---

### POST /api/weight-check/{batch_id}

Log a weight measurement for quality control.

- **Auth Required:** Session only
- **Content-Type:** `application/json`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `size` | string | Yes | Size: `"0.5g"`, `"0.7g"`, or `"1.0g"` |
| `sample_weight` | float | Yes | Weight of 10 pre-rolls in grams |
| `count_at_measurement` | integer | Yes | Production count at time of measurement |

---

### GET /api/weight-analytics/{batch_id}

Get weight tracking analytics for a batch.

- **Auth Required:** Session only

---

### GET /api/centrifuge-history/{strain_name}

Get centrifuge setting change history for a strain from the audit trail.

- **Auth Required:** API key or session

---

### GET /api/recommendations

Get the latest inventory recommendation snapshot.

- **Auth Required:** Session only

---

### POST /api/recommendations/upload

Upload CSV files for processing into inventory recommendations.

- **Auth Required:** Session only
- **Content-Type:** `multipart/form-data`
- **Field:** `files[]` (one or more CSV files)

---

## Production Stages Reference

| Stage | Index | Description |
|-------|-------|-------------|
| Not ground | 0 | Raw material not yet ground |
| Ground | 1 | Material has been ground |
| In progress | 2 | Pre-rolls being produced |
| Finished | 3 | Production complete |
| Waiting on testing | 4 | Sent for lab testing |
| Test passed | 5 | Lab results received and passed |
| Bagging | 6 | Being packaged |
| Done | 7 | Fully complete, ready for archive |

---

## Size Key Reference

| Display | Key | Weight |
|---------|-----|--------|
| 0.5 g | `0_5` | 0.5 grams |
| 0.7 g | `0_7` | 0.7 grams |
| 1.0 g | `1_0` | 1.0 grams |
