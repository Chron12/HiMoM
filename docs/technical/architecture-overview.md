# Architecture Overview

## System Diagram

The PreRollTracker and ApexAPI ecosystem consists of two independent applications that communicate via REST APIs and share data through METRC tracking numbers and synchronization services.

```
                         EXTERNAL SERVICES
    +------------------+  +------------------+  +-----------------+
    | Apex Trading API |  | GitHub Releases  |  | Sentry          |
    | (v1 REST API)    |  | (Encrypted       |  | (Error          |
    |                  |  |  Backups)         |  |  Monitoring)    |
    +--------+---------+  +--------+---------+  +--------+--------+
             |                     |                      |
             |                     |                      |
    +--------v---------+  +--------v---------+            |
    |                  |  |                  |            |
    |    ApexAPI       |  |  PreRollTracker  +<-----------+
    |   (Desktop)      |  |  (Web Server)    |
    |                  |  |                  |
    | +-------------+  |  | +-------------+ |
    | | customtkinter|  |  | |    Flask    | |
    | |   GUI       |  |  | | (Gunicorn)  | |
    | +------+------+  |  | +------+------+ |
    |        |         |  |        |         |
    | +------v------+  |  | +------v------+ |
    | |  Service    |  |  | | Blueprints  | |
    | | Container   |  |  | | (11 total)  | |
    | +------+------+  |  | +------+------+ |
    |        |         |  |        |         |
    | +------v------+  |  | +------v------+ |
    | | Repositories|  |  | | database.py | |
    | | (5 repos)   |  |  | | (SQLite)    | |
    | +------+------+  |  | +------+------+ |
    |        |         |  |        |         |
    | +------v------+  |  | +------v------+ |
    | | apex_data.db|  |  | | preroll_    | |
    | | (SQLite)    |  |  | | tracker.db  | |
    | +-------------+  |  | +-------------+ |
    +------------------+  +------------------+
             |                     ^
             |     REST API        |
             +---------------------+
             (Dashboard API Client)

    +-----------------+  +-----------------+
    | Google Sheets   |  | Pushover API    |
    | (Sync Service)  |  | (Notifications) |
    +-----------------+  +-----------------+
```

## Technology Stack

### PreRollTracker

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Web Framework | Flask 3.0.3 | HTTP request handling, routing, sessions |
| WSGI Server | Gunicorn 21.2.0 | Production multi-worker server |
| Database | SQLite 3 (WAL mode) | All persistent storage |
| Auth | bcrypt 4.0.1 | Password hashing |
| CSRF | Flask-WTF 1.2.2 | Cross-site request forgery protection |
| Rate Limiting | Flask-Limiter 3.5.0 | API rate limiting |
| Monitoring | sentry-sdk | Error tracking and performance monitoring |
| Frontend | Standalone HTML + polish-system.css | No Jinja2 templates; HTML served via send_file |
| PWA | manifest.json + sw.js | Offline capability, installable app |
| Environment | python-dotenv 1.0.0 | .env file loading |
| Math | NumPy | Production rate regression analysis |

### ApexAPI

| Layer | Technology | Purpose |
|-------|-----------|---------|
| GUI Framework | customtkinter 5.0+ | Modern tkinter-based desktop UI |
| HTTP Client (Sync) | requests 2.28+ | Synchronous API calls |
| HTTP Client (Async) | aiohttp 3.8+ | Async API calls with connection pooling |
| Data Processing | pandas 1.5+ | Order data analysis and transformation |
| PDF Generation | reportlab 3.6+ | Packing lists and order forms |
| Database | SQLite 3 | Local caching and state |
| Security | keyring 23.0+ | OS-level credential storage |
| Encryption | cryptography 3.4.8+ | Token security |
| Linting | ruff 0.8+ | Code quality |
| Testing | pytest 8.0+, responses 0.25+ | Test suite with HTTP mocking |

## Data Flow Between PreRollTracker and ApexAPI

The two applications share data in both directions through several integration points:

### ApexAPI to PreRollTracker (Dashboard API Client)

ApexAPI acts as a client to PreRollTracker's REST API via `services/dashboard_api_client.py`:

1. **Batch Inventory Sync** -- `BatchInventorySyncService` reads finished goods from the PreRollTracker dashboard and synchronizes quantities with Apex Trading inventory
2. **Pre-Roll Packing Lists** -- ApexAPI reads active batch data from `/api/data` and finished goods from `/api/finished-goods/` to build packing lists
3. **METRC Number Matching** -- Both systems use METRC tracking numbers as the canonical identifier for cannabis packages; ApexAPI maps Apex Trading product names to METRC numbers via `BatchMappingService`

### PreRollTracker to ApexAPI (Apex Sync)

PreRollTracker has API endpoints for triggering and checking sync status:

1. `/api/apex-sync-status` -- Returns current sync state
2. `/api/apex-sync-trigger` -- Initiates a push of finished goods data
3. Finished goods entries store `apex_auto_inventory`, `apex_units`, and `apex_sku_settings` for ApexAPI integration

### Shared Data Points

| Data | PreRollTracker Field | ApexAPI Field | Flow Direction |
|------|---------------------|---------------|----------------|
| METRC Numbers | `finished_goods.metrc_number` | `batch_mapping_cache.json` | Bidirectional |
| Grams Available | `finished_goods.current_grams` | Dashboard API reads | PRT -> Apex |
| Packed Quantities | `finished_goods.grams_packed` | `preroll_items.packed` | Bidirectional |
| Ordered Quantities | `finished_goods.grams_ordered` | `preroll_items.ordered` | Apex -> PRT |
| SKU Breakdown | `finished_goods.sku_breakdown` | Product parser | PRT -> Apex |

## Request Lifecycle in PreRollTracker

PreRollTracker follows a classic Flask request lifecycle with blueprint-based routing.

### HTTP Request Flow

```
Browser/API Client
       |
       v
  [Gunicorn Worker]
       |
       v
  [Flask App (app.py)]
       |
       +--- CSRF Check (CustomCSRFProtect)
       |    - API routes (/api/*) are exempt
       |    - Web routes require CSRF token
       |
       +--- Rate Limiting (Flask-Limiter)
       |
       +--- Route Matching --> Blueprint
       |
       v
  [Authentication Decorator]
       |
       +--- @login_required
       |    Checks session["logged_in"]
       |    Redirects to /login if missing
       |
       +--- @api_or_login_required
       |    Checks X-API-Key header first (constant-time compare)
       |    Falls back to session auth
       |    Returns 401 JSON if neither succeeds
       |
       v
  [Blueprint Handler]
       |
       v
  [tracker_core.py]
       |
       +--- MODEL (PreRollModel) -- batch CRUD operations
       |    Uses PreRoll dataclass (70+ fields)
       |
       +--- SETTINGS (SettingsManager) -- configuration access
       |
       +--- FinishedGoodsManager -- METRC package management
       |
       +--- InventoryManager -- paper/cone tracking
       |
       +--- WholesaleHoldsManager -- inventory reservations
       |
       v
  [database.py]
       |
       +--- get_connection() -- thread-local SQLite connection
       |    - WAL mode for concurrent reads
       |    - Foreign keys enabled
       |    - 30-second lock timeout
       |
       +--- CRUD operation (save_batch, get_all_batches, etc.)
       |
       +--- log_audit() -- change tracking
       |
       v
  [preroll_tracker.db]  (SQLite)
       |
       v
  [JSON Response / HTML Page]
```

### View Routes vs API Routes

PreRollTracker serves two types of responses:

1. **View Routes** (`blueprints/views.py`) -- Serve standalone HTML files via `send_file()`. These HTML pages are fully self-contained with embedded JavaScript that calls API endpoints. They are NOT Jinja2 templates.

2. **API Routes** (`blueprints/api_*.py`) -- Return JSON responses. These are consumed by both the standalone HTML pages and external clients like ApexAPI.

### Background Processes

Two daemon threads run alongside the Flask application:

1. **Learning Processor** -- Runs every 5 minutes via `start_learning_background_thread()`. Calls `LearningProcessor.process_new_outcomes()` to update centrifuge recommendations based on production results.

2. **Backup Scheduler** -- `BackupScheduler` from `backup_manager.py` runs every 6 hours. Creates AES-256-CBC encrypted SQLite backups and uploads to GitHub Releases. Uses filesystem locks (`fcntl`) to ensure only one Gunicorn worker runs backups.

## Request Lifecycle in ApexAPI

ApexAPI follows an event-driven desktop application pattern with dependency injection.

### GUI Event Flow

```
User Action (click, input)
       |
       v
  [customtkinter Widget]
       |
       v
  [GUI Module Handler]
       |  (main_gui.py, pre_roll_packing_list.py, etc.)
       |
       v
  [ServiceContainer]
       |
       +--- get_order_service()
       +--- get_cache_service()
       +--- get_config_service()
       +--- get_print_service()
       +--- get_batch_mapping_service()
       +--- get_order_completion_service()
       |
       v
  [Service Layer]
       |
       +--- Sync Path: OrderService --> ApexAPIClient --> requests.Session
       |
       +--- Async Path: AsyncOrderService --> AsyncApexAPIClient --> aiohttp
       |    (Background thread with its own event loop)
       |
       +--- Cache Check: CacheService --> in-memory / disk cache
       |
       +--- Event Publishing: EventBus.publish(EventType.*)
       |
       v
  [Repository Layer]
       |
       +--- OrderRepository.get_connection() -- context manager
       |    - Per-operation connections (not thread-local)
       |    - Foreign keys enabled
       |    - Automatic transaction management
       |
       +--- ConfigRepository
       +--- PreRollRepository
       +--- EdiblesRepository
       |
       v
  [apex_data.db]  (SQLite)
```

### Service Container Initialization Order

The `ServiceContainer.initialize()` method creates services in dependency order:

1. **EventBus** -- Singleton pub/sub message broker
2. **ConfigService** -- Reads `apex_config.json` and keyring
3. **ApexAPIClient** (sync) -- HTTP client with Bearer token auth
4. **AsyncApexAPIClient** (async) -- aiohttp-based async client
5. **OrderRepository** + **ConfigRepository** -- Database access
6. **CacheService** -- Multi-level cache with TTL
7. **OrderService** -- Business logic for order management
8. **AsyncOrderService** -- Async order operations with event publishing
9. **CacheWarmer** -- Background cache preloading
10. **CacheLogger** -- Cache performance monitoring
11. **PrintService** -- PDF generation and printing
12. **BatchMappingService** -- METRC-to-product mapping
13. **BatchInventorySyncService** -- Dashboard sync automation
14. **PreRollRepository** + **OrderCompletionService** -- Packing workflow

After all services are created, event subscriptions are wired up and the cache warming thread starts.

### Event-Driven Communication

Components communicate via the EventBus without direct dependencies:

```
CONFIG_CHANGED  -----> CacheService.clear_cache('api_responses')
                -----> PrintService.update_license_number()

API_TOKEN_UPDATED ---> CacheService.clear_cache('api_responses')
                   --> CacheService.clear_cache('inventory')
                   --> CacheService.clear_cache('order_details')

ORDERS_LOADED   -----> GUI.refresh_order_list()

ERROR_OCCURRED  -----> logging.error()
```

## Authentication Architecture

### PreRollTracker Authentication

PreRollTracker uses a dual authentication system:

**Session-Based Auth (Web UI)**

- Admin logs in via `/login` with username/password
- Password verified using bcrypt (`auth_utils.py::PasswordManager`)
- Session cookie set with `session["logged_in"] = True`
- 30-day session lifetime with HttpOnly, SameSite=Lax cookies
- CSRF protection on all non-API routes via Flask-WTF

**API Key Auth (Programmatic Access)**

- Clients send `X-API-Key` header
- Key validated via constant-time comparison (`secrets.compare_digest`)
- API key stored in settings database table
- Key can be regenerated via `/api/api-key/regenerate`

**Password Recovery**

- Recovery keys use format `HARVEST-XXXX-XXXX-XXXX`
- Keys are bcrypt-hashed before storage
- Recovery flow: `/forgot-password` -> verify recovery key -> `/reset-password`

### ApexAPI Authentication

ApexAPI authenticates with the Apex Trading API using Bearer tokens:

**Token Storage**

- Primary: OS keyring via `keyring` library (`SecureConfigManager`)
- Fallback: JSON config file (with migration path to keyring)
- Service name: `ApexTradingAPI`, key: `api_token`

**Token Flow**

1. User enters API token in GUI settings
2. `SecureConfigManager.store_api_token()` saves to keyring
3. `ServiceContainer` reads token via `ConfigService.get_api_token()`
4. Both sync and async API clients receive the token
5. Token included as `Authorization: Bearer <token>` header

**Dashboard API Auth**

When ApexAPI calls PreRollTracker's API, it uses the `X-API-Key` header with the key configured in its settings.

## Caching Strategy Overview

### PreRollTracker Caching

PreRollTracker has minimal application-level caching by design:

- **SQLite WAL Mode** -- Enables concurrent reads during writes, acting as a natural read cache
- **Thread-Local Connections** -- Each thread maintains its own connection, avoiding lock contention
- **Rate Caching** -- Production rates are cached in `cached_production_rate` and `rate_metrics` fields to avoid recalculation on every request
- **No HTTP Cache Headers** -- The HTML dashboard pages poll `/api/batches/last-updated` to detect changes and refresh only when data has changed

### ApexAPI Caching

ApexAPI implements a sophisticated multi-level caching system:

**CacheService** (`services/cache_service.py`)

- In-memory dictionary-based cache with TTL expiration
- Disk-based cache using JSON files for persistence
- Cache categories: `api_responses`, `inventory`, `order_details`, `batch_mapping`
- Automatic expiration and eviction

**CacheWarmer** (`cache/cache_warmer.py`)

- Background async task warming commonly accessed data
- Configurable intervals per data type:
  - Orders list: every 2 minutes
  - Order details: every 30 minutes
  - Inventory: daily
  - Predictive details: every 5 minutes (pre-fetches likely-needed orders)
- Access pattern tracking to optimize warming priorities
- Runs in a dedicated thread with its own asyncio event loop

**CacheLogger** (`services/cache_logger.py`)

- Monitors cache hit/miss ratios
- Console and file logging of cache performance
- Configurable stats interval (default: 5 minutes)

**Cache Invalidation Events**

The EventBus triggers cache invalidation when:

- `CONFIG_CHANGED` -- Clears API response caches if API-related config changes
- `API_TOKEN_UPDATED` -- Clears all API, inventory, and order detail caches
- `CACHE_CLEARED` -- Published after manual cache clear operations

## Error Handling and Monitoring

### PreRollTracker Error Handling

PreRollTracker uses a layered error handling strategy:

**Sentry Integration**

The application initializes Sentry SDK at startup in `app.py` with:

- Release tracking via git commit SHA (e.g., `pre-roll-tracker@abc123def456`)
- Low sampling rates (5% traces, 5% profiles) to minimize performance overhead
- A `before_send` filter that drops common network errors (ConnectionReset, BrokenPipe, Timeout) to reduce noise
- PII sending disabled (`send_default_pii=False`)
- Environment tagging (development/production)

**Flask Error Handlers**

The application registers a custom handler for HTTP 413 (Request Entity Too Large) that returns JSON for API routes and a flash message redirect for web routes. The maximum upload size is 16 MB.

**Blueprint-Level Error Handling**

Each API blueprint wraps its handlers in try/except blocks that:

1. Log the full exception via `logger.exception()`
2. Return a generic JSON error (`{"error": "An internal error occurred"}`) with HTTP 500
3. Never expose stack traces or internal details to clients

**Database Error Handling**

`database.py` uses SQLite's 30-second lock timeout to handle concurrent write contention. Transaction management functions (`begin_exclusive_transaction`, `commit_transaction`, `rollback_transaction`) provide explicit control for operations that need atomicity, such as inventory updates where a race condition could cause double-counting.

### ApexAPI Error Handling

**Event-Based Error Reporting**

Errors in services are published to the EventBus as `ERROR_OCCURRED` events. The main GUI subscribes to these events and displays error messages to the user via dialog boxes or status bar updates.

**Async Error Handling**

The `AsyncApexAPIClient` wraps all aiohttp calls with timeout handling, connection error catching, and retry logic. Failed requests do not crash the application; they return error dictionaries that the calling service can inspect.

**Repository Error Handling**

`BaseRepository` uses context managers for all database operations:

```python
@contextmanager
def get_connection(self):
    conn = sqlite3.connect(self.db_path)
    try:
        yield conn
    except sqlite3.Error as e:
        conn.rollback()
        logging.error("Database error: %s", e)
        raise
    finally:
        conn.close()
```

This ensures connections are always closed and transactions are rolled back on error.

**Cache Error Resilience**

The `CacheService` treats cache failures as non-fatal. If reading from cache raises an exception, the service returns `None` (cache miss) and logs the error. The calling code then falls through to fetch data from the API. This means cache corruption or disk issues never prevent the application from functioning.

## Security Architecture

### PreRollTracker Security Measures

**Transport Security**

- `SESSION_COOKIE_SECURE = True` in production (requires HTTPS)
- `SESSION_COOKIE_HTTPONLY = True` prevents JavaScript access to session cookies
- `SESSION_COOKIE_SAMESITE = "Lax"` prevents CSRF attacks via cross-origin requests
- Flask-Talisman is included in dependencies for Content Security Policy headers

**Input Validation**

- `helpers.py::validate_strain_data()` validates percentage ranges, centrifuge parameters, and METRC number consistency
- `MarkupSafe` is installed and Jinja2 autoescape is explicitly enabled
- `static/escape-utils.js` provides client-side XSS sanitization for dynamically rendered content
- `MAX_CONTENT_LENGTH = 16 MB` prevents memory exhaustion from large uploads

**CSRF Protection**

The `CustomCSRFProtect` subclass exempts API routes (`/api/*`) from CSRF validation because standalone HTML pages (served via `send_file`) cannot include server-generated CSRF tokens. API routes are instead protected by the `@api_or_login_required` decorator which requires either a valid session or API key.

**Secret Management**

- `SECRET_KEY` is required at startup; the app raises `RuntimeError` if missing
- Admin password is stored as a bcrypt hash, never in plaintext
- API keys use constant-time comparison via `secrets.compare_digest()` to prevent timing attacks
- The `BACKUP_ENCRYPTION_KEY` is used with AES-256-CBC via OpenSSL for off-site backups

### ApexAPI Security Measures

**Credential Storage**

- API tokens are stored in the OS keyring (macOS Keychain, Windows Credential Manager, Linux Secret Service)
- If keyring is unavailable, tokens fall back to the JSON config file with a migration warning
- The `SecureConfigManager.save_config()` method explicitly excludes the `api_token` key from the JSON file
- Token migration happens automatically: on load, if a token is found in JSON and keyring is available, it migrates to keyring and removes from JSON

**Network Security**

- All API communication uses HTTPS (base URL: `https://app.apextrading.com/api/v1`)
- Bearer token authentication for Apex Trading API
- X-API-Key header authentication for PreRollTracker dashboard API
- Request timeouts configured (10s connect, 30s read) to prevent hanging connections

## Deployment Architecture

### PreRollTracker Production Deployment

PreRollTracker runs on a Linux server behind a reverse proxy:

```
Internet
    |
    v
[Nginx Reverse Proxy]
    |
    +--- SSL Termination (Let's Encrypt)
    +--- Static file serving
    +--- Proxy to Gunicorn
    |
    v
[Gunicorn (4 workers)]
    |
    +--- Worker 1: Flask app + backup scheduler thread
    +--- Worker 2: Flask app (backup lock prevents duplicate backups)
    +--- Worker 3: Flask app
    +--- Worker 4: Flask app
    |
    v
[preroll_tracker.db] (SQLite with WAL)
```

Key deployment details:

- Gunicorn binds to `0.0.0.0:5000` with 4 worker processes
- Only one worker acquires the backup filesystem lock, preventing duplicate backups
- Rotating log files with 10 MB max size and 10 backup files
- The `deploy.sh` script handles git pull, dependency installation, and service restart
- Live at `himomstats.online`

### ApexAPI Distribution

ApexAPI is distributed as a standalone desktop executable:

- **macOS:** Built with PyInstaller using `apex_gui.spec`, distributed as `.app` bundle
- **Windows:** Built with PyInstaller using `apex_gui_windows.spec`, distributed as `.exe`
- Both builds bundle all Python dependencies including customtkinter, aiohttp, pandas, and reportlab
- Configuration files (`apex_config.json`) and cache directories are created in the executable's directory on first run
- The executable can be run without a Python installation

## Performance Considerations

### PreRollTracker Performance

- **SQLite WAL mode** allows multiple concurrent readers with one writer, sufficient for the expected load (single production facility)
- **Thread-local connections** avoid connection pool overhead while preventing cross-thread SQLite issues
- **Batch data serialization** excludes `rate_history` from default `/api/data` responses for performance (opt-in via `?include_history=true`)
- **Polling optimization** via `/api/batches/last-updated` allows the dashboard to check for changes with a lightweight timestamp comparison before doing a full data refresh
- **Background processing** for learning and backups runs on daemon threads that do not block request handling

### ApexAPI Performance

- **Async HTTP client** allows multiple API requests to run concurrently without blocking the GUI
- **Cache warming** preloads frequently accessed data so most user interactions are served from cache
- **Predictive warming** pre-fetches order details for orders likely to be viewed based on access patterns
- **Background threads** keep the GUI responsive during API calls and cache operations
- **Access pattern tracking** in the CacheWarmer allows it to prioritize warming the most frequently accessed data

## Blueprint Architecture Detail

### PreRollTracker Blueprint Registration

All 11 blueprints are registered in `app.py` after Flask initialization:

```python
app.register_blueprint(pwa_bp)         # PWA support (manifest, service worker, icons)
app.register_blueprint(auth_bp)        # Authentication (login, logout, password reset)
app.register_blueprint(views_bp)       # HTML page serving (dashboard, archive, stats)
app.register_blueprint(admin_bp)       # Admin interface (batch CRUD, settings)
app.register_blueprint(api_batches_bp) # Batch API (/api/data, /api/batch/*)
app.register_blueprint(api_centrifuge_bp)      # Centrifuge API (/api/centrifuge/*)
app.register_blueprint(api_finished_goods_bp)  # Finished goods API (/api/finished-goods/*)
app.register_blueprint(api_inventory_bp)       # Inventory API (/api/inventory/*)
app.register_blueprint(api_snapshots_bp)       # Snapshot API (/api/snapshots/*)
app.register_blueprint(api_wholesale_bp)       # Wholesale API (/api/wholesale/*)
app.register_blueprint(api_misc_bp)            # Miscellaneous API endpoints
```

Each blueprint uses a descriptive name for URL rule generation. The API blueprints use URL prefixes that namespace their routes (e.g., `api_finished_goods` routes are prefixed with `/api/finished-goods`), while the views and auth blueprints register at the root.

### Route Count by Blueprint

The total API surface includes approximately 80+ routes:

| Blueprint | Route Count | Key Endpoints |
|-----------|-------------|---------------|
| views | 9 | Dashboard, archive, stats, finished goods, wholesale, inventory, centrifuge |
| auth | 4 | Login, logout, forgot-password, reset-password |
| admin | 13 | Dashboard, add/edit/delete batch, settings, analytics, archive, audit, inventory, centrifuge, recommendations |
| api_batches | 12 | Data, archive, counts, plan, reorder, centrifuge settings, priority mode, progress |
| api_finished_goods | 20+ | CRUD, deduct, add, pack, sync, Apex integration, history, calculator |
| api_inventory | 3 | Get, update, settings |
| api_wholesale | 5 | Inventory, hold CRUD, holds list, last-updated |
| api_centrifuge | 8 | Calculate, compare, curve-data, settings-guide, impulse, target-match, batch-comparison, impulse-zones |
| api_snapshots | 5 | History, get snapshot, compare-detailed, insights, export-csv |
| api_misc | 20+ | Version, backup, settings, API key, audit, overview, production history, Apex sync, Pushover, weight checks, centrifuge recommendations, fill gauge |
| pwa | 5 | Manifest, service worker, icons, favicon |

### The Admin Blueprint

The `admin.py` blueprint is the largest file in the codebase at over 11,000 lines. Unlike the API blueprints which return JSON, the admin blueprint renders complete HTML pages with embedded CSS and JavaScript. This approach was chosen for operational reliability -- the admin interface works even when static file serving has issues.

Admin routes use the `@login_required` decorator (session-only, no API key auth) and serve forms for:

- Adding new production batches with all strain, testing, and centrifuge fields
- Editing existing batches (full form with validation)
- Production planning with allocation previews
- Application settings (password changes, API key management)
- Inventory management with low-stock alerts
- Bulk inventory upload via CSV
- Analytics dashboards with centrifuge trend data

## Async Architecture in ApexAPI

### Threading Model

ApexAPI uses a multi-threaded architecture to keep the GUI responsive:

```
Main Thread (tkinter event loop)
    |
    +--- GUI rendering and user interaction
    |
    +--- Synchronous API calls (short, blocking)
    |
Background Thread 1: Cache Warming
    |
    +--- asyncio event loop
    |
    +--- CacheWarmer.run_warming_cycle()
    |
    +--- CacheWarmer.schedule_warming(interval)
    |
Background Thread 2: Batch Inventory Sync (optional)
    |
    +--- Periodic sync of inventory data
```

The cache warming thread creates its own asyncio event loop because tkinter's main loop is not async-compatible. This allows the `AsyncApexAPIClient` to make concurrent HTTP requests without blocking the GUI.

### Sync vs Async API Clients

ApexAPI provides two API client implementations:

**ApexAPIClient** (`api_client.py`) -- Uses `requests.Session` for synchronous HTTP calls. Used for simple, sequential operations where the result is needed immediately (e.g., testing connection, single order fetch).

**AsyncApexAPIClient** (`api/async_client.py`) -- Uses `aiohttp.ClientSession` for async HTTP calls. Used for bulk operations where multiple requests can run concurrently (e.g., fetching details for 50 orders, warming multiple cache entries simultaneously).

Both clients share the same Bearer token and base URL. The `ServiceContainer` creates and configures both during initialization.

### Google Sheets Integration

ApexAPI integrates with Google Sheets for collaborative packing list management:

1. **GoogleSheetsClient** (`services/google_sheets_client.py`) -- Handles authentication and raw API calls to Google Sheets
2. **GoogleSheetsSyncService** (`services/google_sheets_sync_service.py`) -- Bidirectional sync between the local packing list and a shared Google Sheet
3. The sync allows multiple team members to update packed quantities from different devices, with changes flowing back into the desktop application
