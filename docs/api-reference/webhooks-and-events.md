# Webhooks and Events Reference

**Last Updated:** 2026-02-28

This document covers the event-driven architecture across PreRollTracker and ApexAPI, including polling endpoints, the ApexAPI Event Bus, cache invalidation, and background job triggers.

---

## PreRollTracker Polling Endpoints

PreRollTracker does not use WebSockets or server-sent events. Instead, it provides lightweight polling endpoints that clients can call at regular intervals to detect data changes. Each endpoint returns a timestamp or fingerprint that changes when underlying data is modified.

### Polling Architecture

The recommended polling pattern:

1. Call the `last-updated` endpoint on an interval (e.g., every 5-10 seconds).
2. Compare the returned timestamp/fingerprint to the previously stored value.
3. If changed, fetch the full data from the corresponding data endpoint.
4. Store the new timestamp/fingerprint for the next comparison.

### Batch Polling

**Endpoint:** `GET /api/batches/last-updated`

**Auth:** API key or session

**Returns:** The timestamp of the most recent audit log entry.

```json
{
  "timestamp": "2026-02-28T14:30:00.000Z"
}
```

**When it changes:** Any batch field update (stage change, count update, plan change, centrifuge settings, etc.) writes to the audit log, updating this timestamp.

**Data endpoint to refresh:** `GET /api/data`

---

### Finished Goods Polling

**Endpoint:** `GET /api/finished-goods/last-updated`

**Auth:** API key or session

**Returns:** The timestamp of the most recent finished goods history entry.

```json
{
  "timestamp": "2026-02-28T14:30:00.000Z"
}
```

**When it changes:** Any finished goods operation (add package, deduct inventory, update fields, add inventory, physical override) records a history entry.

**Data endpoint to refresh:** `GET /api/finished-goods/`

---

### Wholesale Polling

**Endpoint:** `GET /api/wholesale/last-updated`

**Auth:** Session only

**Returns:** A composite fingerprint combining three data points.

```json
{
  "fingerprint": "2026-02-28T14:30:00Z|2026-02-28T12:00:00Z|5"
}
```

**Fingerprint format:** `{latest_hold_timestamp}|{latest_fg_history_timestamp}|{total_hold_count}`

**When it changes:** Creating or releasing wholesale holds, or any finished goods inventory change.

**Data endpoints to refresh:** `GET /api/wholesale/inventory` and `GET /api/wholesale/holds`

---

### Polling Implementation Example

```javascript
// Client-side polling example
class DataPoller {
  constructor(endpoint, dataEndpoint, interval = 5000) {
    this.endpoint = endpoint;
    this.dataEndpoint = dataEndpoint;
    this.interval = interval;
    this.lastValue = null;
    this.timer = null;
  }

  start() {
    this.timer = setInterval(() => this.check(), this.interval);
  }

  stop() {
    clearInterval(this.timer);
  }

  async check() {
    const response = await fetch(this.endpoint, {
      headers: { "X-API-Key": "YOUR_KEY" }
    });
    const data = await response.json();
    const currentValue = data.timestamp || data.fingerprint;

    if (this.lastValue !== null && currentValue !== this.lastValue) {
      // Data changed -- refresh
      await this.refreshData();
    }
    this.lastValue = currentValue;
  }

  async refreshData() {
    const response = await fetch(this.dataEndpoint, {
      headers: { "X-API-Key": "YOUR_KEY" }
    });
    const data = await response.json();
    // Handle updated data...
  }
}

// Usage
const batchPoller = new DataPoller(
  "/api/batches/last-updated",
  "/api/data",
  5000
);
batchPoller.start();
```

---

## ApexAPI Event Bus

ApexAPI uses a singleton, thread-safe Event Bus for decoupled publish-subscribe communication between components. This is an in-process event system (not network-based webhooks).

### Event Bus Architecture

- **Pattern:** Publish-Subscribe (Observer)
- **Threading:** Thread-safe with `RLock` for subscriptions
- **Singleton:** Global `event_bus` instance shared across the application
- **History:** Maintains last 1,000 events in memory
- **Priority:** Subscribers can set priority (higher = called first)
- **One-shot:** Subscriptions can be configured to fire only once

### Event Object Structure

```python
@dataclass
class Event:
    event_type: EventType    # Enum value identifying the event
    data: Any = None         # Payload (any type)
    source: str | None = None  # Component that published the event
    timestamp: datetime       # Auto-generated creation time
    event_id: str | None = None  # Auto-generated unique ID
```

### All Event Types

#### Order Events

| Event Type | Value | Trigger | Typical Data |
|-----------|-------|---------|-------------|
| `ORDERS_LOADED` | `orders_loaded` | Initial order data fetch from Apex API | List of Order objects |
| `ORDERS_REFRESHED` | `orders_refreshed` | Periodic order data refresh | Updated order list |
| `ORDER_UPDATED` | `order_updated` | Single order modified | Order object |
| `ORDER_STATUS_CHANGED` | `order_status_changed` | Order status changes (e.g., Pending to Shipped) | `{order_id, old_status, new_status}` |
| `ORDER_PRINTED` | `order_printed` | Order form printed | Order object |
| `ORDER_UNPRINTED` | `order_unprinted` | Print flag cleared | Order object |
| `NEW_ORDERS_DETECTED` | `new_orders_detected` | New orders found during refresh | List of new Order objects |

#### API Connection Events

| Event Type | Value | Trigger | Typical Data |
|-----------|-------|---------|-------------|
| `API_CONNECTION_ESTABLISHED` | `api_connection_established` | Successful API authentication | `{base_url, token_preview}` |
| `API_CONNECTION_LOST` | `api_connection_lost` | API becomes unreachable | Error details |
| `API_TOKEN_UPDATED` | `api_token_updated` | Bearer token refreshed | Token metadata |
| `API_ERROR` | `api_error` | API request failed | `{endpoint, status_code, error}` |
| `API_REQUEST_STARTED` | `api_request_started` | API request initiated | `{endpoint, method}` |
| `API_REQUEST_COMPLETED` | `api_request_completed` | API request finished | `{endpoint, status_code, duration_ms}` |

#### Print Events

| Event Type | Value | Trigger | Typical Data |
|-----------|-------|---------|-------------|
| `PRINT_STARTED` | `print_started` | Print job initiated | `{order_id, printer}` |
| `PRINT_COMPLETED` | `print_completed` | Print job finished | `{order_id, pages}` |
| `PRINT_FAILED` | `print_failed` | Print job error | `{order_id, error}` |
| `PRINTER_SELECTED` | `printer_selected` | Printer changed | `{printer_name}` |
| `PRINTER_STATUS_CHANGED` | `printer_status_changed` | Printer online/offline | `{printer, status}` |

#### Configuration Events

| Event Type | Value | Trigger | Typical Data |
|-----------|-------|---------|-------------|
| `CONFIG_CHANGED` | `config_changed` | Configuration value modified | `{key, old_value, new_value}` |
| `CONFIG_LOADED` | `config_loaded` | Configuration file loaded | Config dict |
| `CONFIG_SAVED` | `config_saved` | Configuration persisted to disk | Config dict |

#### UI Events

| Event Type | Value | Trigger | Typical Data |
|-----------|-------|---------|-------------|
| `UI_FILTER_CHANGED` | `ui_filter_changed` | Order filter updated | `{filter_type, value}` |
| `UI_SELECTION_CHANGED` | `ui_selection_changed` | Order selected in list | `{order_id}` |
| `UI_REFRESH_REQUESTED` | `ui_refresh_requested` | Manual refresh button clicked | None |
| `UI_THEME_CHANGED` | `ui_theme_changed` | Theme toggled | `{theme}` |

#### Cache Events

| Event Type | Value | Trigger | Typical Data |
|-----------|-------|---------|-------------|
| `CACHE_CLEARED` | `cache_cleared` | All cached data invalidated | `{reason}` |
| `CACHE_UPDATED` | `cache_updated` | Specific cache entry updated | `{cache_key, ttl}` |
| `CACHE_EXPIRED` | `cache_expired` | Cache entry TTL expired | `{cache_key}` |

#### Auto-Refresh Events

| Event Type | Value | Trigger | Typical Data |
|-----------|-------|---------|-------------|
| `AUTO_REFRESH_ENABLED` | `auto_refresh_enabled` | Auto-refresh turned on | `{interval_seconds}` |
| `AUTO_REFRESH_DISABLED` | `auto_refresh_disabled` | Auto-refresh turned off | None |
| `AUTO_REFRESH_INTERVAL_CHANGED` | `auto_refresh_interval_changed` | Interval modified | `{old_interval, new_interval}` |
| `AUTO_REFRESH_TRIGGERED` | `auto_refresh_triggered` | Scheduled refresh fired | `{trigger_time}` |

#### System Events

| Event Type | Value | Trigger | Typical Data |
|-----------|-------|---------|-------------|
| `APPLICATION_STARTED` | `application_started` | Application initialization complete | `{version}` |
| `APPLICATION_CLOSING` | `application_closing` | Application shutdown initiated | None |
| `ERROR_OCCURRED` | `error_occurred` | Unhandled error caught | `{error, traceback}` |
| `WARNING_OCCURRED` | `warning_occurred` | Non-fatal issue detected | `{message}` |
| `INFO_MESSAGE` | `info_message` | Informational message | `{message}` |

#### Database Events

| Event Type | Value | Trigger | Typical Data |
|-----------|-------|---------|-------------|
| `DATABASE_CONNECTED` | `database_connected` | SQLite database opened | `{db_path}` |
| `DATABASE_ERROR` | `database_error` | Database operation failed | `{error, query}` |
| `DATABASE_BACKUP_COMPLETED` | `database_backup_completed` | Database backup finished | `{backup_path, size}` |

#### Security Events

| Event Type | Value | Trigger | Typical Data |
|-----------|-------|---------|-------------|
| `SECURE_STORAGE_AVAILABLE` | `secure_storage_available` | OS keychain accessible | None |
| `SECURE_STORAGE_UNAVAILABLE` | `secure_storage_unavailable` | OS keychain not available | `{fallback}` |
| `TOKEN_MIGRATED` | `token_migrated` | API token moved to secure storage | None |

#### Inventory Sync Events

| Event Type | Value | Trigger | Typical Data |
|-----------|-------|---------|-------------|
| `INVENTORY_SYNC_STARTED` | `inventory_sync_started` | Sync with PreRollTracker begins | `{sync_type}` |
| `INVENTORY_SYNCED` | `inventory_synced` | Sync completed successfully | `{packages_synced, grams_total}` |
| `INVENTORY_SYNC_FAILED` | `inventory_sync_failed` | Sync failed | `{error}` |
| `BATCH_QUANTITY_UPDATED` | `batch_quantity_updated` | Batch quantity changed via sync | `{batch_id, old_qty, new_qty}` |

---

### Event Bus Usage Examples

#### Publishing an Event

```python
from events.event_bus import event_bus
from events.event_types import EventType

# Simple publish
event_bus.publish(EventType.ORDERS_LOADED, data=orders_list, source="order_service")

# Publish with custom event object
from events.event_bus import Event
event = Event(
    event_type=EventType.ORDER_STATUS_CHANGED,
    data={"order_id": 123, "old_status": "Pending", "new_status": "Shipped"},
    source="api_client"
)
event_bus.publish_event(event)
```

#### Subscribing to Events

```python
from events.event_bus import event_bus
from events.event_types import EventType

def on_orders_loaded(event):
    orders = event.data
    print(f"Loaded {len(orders)} orders from {event.source}")

# Standard subscription
sub_id = event_bus.subscribe(EventType.ORDERS_LOADED, on_orders_loaded)

# Priority subscription (called before lower-priority)
sub_id = event_bus.subscribe(EventType.ORDERS_LOADED, on_orders_loaded, priority=10)

# One-shot subscription (auto-unsubscribes after first call)
sub_id = event_bus.subscribe(EventType.API_CONNECTION_ESTABLISHED, on_connected, once=True)
```

#### Unsubscribing

```python
# By subscription ID
event_bus.unsubscribe(sub_id)

# All subscribers for an event type
event_bus.unsubscribe_all(EventType.ORDERS_LOADED)

# Clear everything
event_bus.clear_all_subscriptions()
```

#### Synchronous Waiting

```python
# Block until an event occurs (with timeout)
event = event_bus.wait_for_event(EventType.API_CONNECTION_ESTABLISHED, timeout=30.0)
if event:
    print("Connected!")
else:
    print("Timeout waiting for connection")
```

#### Getting Statistics

```python
stats = event_bus.get_stats()
# {
#   "events_published": 1250,
#   "total_callbacks_called": 3800,
#   "callback_errors": 2,
#   "subscriptions_created": 45,
#   "subscriptions_removed": 12,
#   "subscription_counts": {"orders_loaded": 3, "cache_updated": 2},
#   "total_subscriptions": 33,
#   "event_history_size": 500,
#   "max_history_size": 1000
# }
```

---

## Cache Invalidation Events

### PreRollTracker Cache Behavior

PreRollTracker uses in-memory caching for batch data (`MODEL.get_active_as_dict()`). Cache is invalidated when:

1. **Batch update** -- Any call to `MODEL.update()` invalidates the cached batch list.
2. **Batch archive/unarchive** -- Changes to archive status invalidate active batch cache.
3. **Reorder** -- Reordering batches updates `display_order` and invalidates cache.
4. **Inventory changes** -- Inventory updates through `INVENTORY_MANAGER.update_inventory()`.
5. **Finished goods changes** -- Any CRUD operation on finished goods.

### ApexAPI Cache Behavior

ApexAPI uses a `CacheService` with TTL-based expiration:

- **Order cache** -- Refreshed on `ORDERS_REFRESHED` events. TTL-based with configurable interval.
- **Inventory cache** -- Invalidated on `INVENTORY_SYNCED` events.
- **Config cache** -- Invalidated on `CONFIG_CHANGED` events.

The `CACHE_CLEARED`, `CACHE_UPDATED`, and `CACHE_EXPIRED` events allow other components to react to cache state changes.

---

## Background Job Triggers

### PreRollTracker Background Jobs

#### 1. Learning Processor

- **Trigger:** Runs on a 5-minute loop (`time.sleep(300)`)
- **Purpose:** Processes new centrifuge outcomes to improve fill gauge recommendations
- **Started by:** `start_learning_background_thread()` at app startup
- **Thread:** Daemon thread (dies with main process)

```python
# Background loop
while True:
    processor.process_new_outcomes()
    time.sleep(300)  # 5 minutes
```

#### 2. Backup Scheduler

- **Trigger:** Scheduled intervals managed by `BackupScheduler`
- **Purpose:** Creates periodic SQLite database backups
- **Started by:** `_backup_scheduler = BackupScheduler(); _backup_scheduler.start()` at app startup
- **Health check:** `GET /api/backup-status`

#### 3. Testing Alerts

- **Trigger:** Checked every 30 minutes via `check_testing_alerts()` (Qt timer in desktop app)
- **Purpose:** Sends desktop notifications for batches stuck in "Waiting on testing" stage
- **Condition:** Batch in stage 4 for longer than `test_alert_hours` setting

#### 4. Pushover Stock Alerts

- **Trigger:** Manually via `POST /api/pushover/check-alerts` or automatically during inventory operations
- **Purpose:** Sends push notifications when finished goods stock falls below warning/critical thresholds
- **Cooldown:** Configurable hours between repeat alerts per strain

### ApexAPI Background Jobs

#### 1. Auto-Refresh

- **Trigger:** `AUTO_REFRESH_TRIGGERED` event on configurable interval
- **Purpose:** Periodically fetches fresh order data from Apex Trading API
- **Events fired:** `ORDERS_REFRESHED`, `NEW_ORDERS_DETECTED` (if new orders found)

#### 2. Inventory Sync (PreRollTracker Integration)

- **Trigger:** Manual or scheduled
- **Purpose:** Syncs finished goods inventory between ApexAPI and PreRollTracker dashboard
- **Flow:**
  1. `INVENTORY_SYNC_STARTED` event published
  2. ApexAPI queries PreRollTracker `GET /api/finished-goods/`
  3. Processes and maps inventory data
  4. `INVENTORY_SYNCED` event published on success
  5. `INVENTORY_SYNC_FAILED` event published on failure

#### 3. Cache Warming

- **Module:** `cache/cache_warmer.py`
- **Purpose:** Pre-populates cache with frequently accessed data on startup
- **Trigger:** Application startup, after `APPLICATION_STARTED` event

---

## Cross-System Communication

### PreRollTracker to ApexAPI

ApexAPI polls PreRollTracker's API endpoints for data synchronization:

```
ApexAPI (client) --> PreRollTracker (server)
  GET /api/data                    # Active batch data
  GET /api/finished-goods/         # Finished goods inventory
  GET /api/finished-goods/summary  # Inventory summary
  GET /api/apex-sync-status        # Check if sync was requested
```

### ApexAPI to PreRollTracker

ApexAPI can trigger operations on PreRollTracker:

```
ApexAPI (client) --> PreRollTracker (server)
  POST /api/apex-sync-trigger      # Request sync
  POST /api/finished-goods/{metrc}/deduct   # Deduct inventory
  POST /api/finished-goods/{metrc}/add      # Add inventory
```

### Sync Trigger Flow

1. User clicks "Sync" in ApexAPI GUI or scheduled sync fires.
2. ApexAPI calls `POST /api/apex-sync-trigger` on PreRollTracker.
3. PreRollTracker updates `apex_sync_requested_at` timestamp.
4. ApexAPI then reads from PreRollTracker's API endpoints to pull data.
5. `INVENTORY_SYNCED` event published in ApexAPI on completion.

---

## Error Handling in Events

The Event Bus has built-in error isolation:

- **Callback errors do not propagate** -- If a subscriber callback raises an exception, it is caught and logged. Other subscribers still receive the event.
- **Error tracking** -- Each subscription tracks its errors with timestamps and tracebacks.
- **Stats available** -- `event_bus.get_stats()` includes `callback_errors` count.
- **Subscription details** -- `event_bus.get_subscription_details()` shows per-subscription error counts and recent errors.

```python
# Check for problematic subscribers
details = event_bus.get_subscription_details(EventType.ORDERS_LOADED)
for sub in details:
    if sub["error_count"] > 0:
        print(f"Subscription {sub['subscription_id']} has {sub['error_count']} errors")
        for error in sub["recent_errors"]:
            print(f"  {error['timestamp']}: {error['error']}")
```
