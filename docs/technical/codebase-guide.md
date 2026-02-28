# Codebase Guide

## PreRollTracker Directory Structure

PreRollTracker is a Flask web application serving a cannabis pre-roll production tracking dashboard. The project root is at `~/PycharmProjects/PreRollTracker/`.

### Root-Level Files

| File | Purpose |
|------|---------|
| `app.py` | Flask application factory. Initializes Flask, Sentry, CSRF, rate limiting, blueprints, and background threads. This is the main application entry point. |
| `run.py` | Production entry point. Imports app from `app.py`, sets production config, sets up logging. Run with `gunicorn run:app`. |
| `tracker_core.py` | Core business logic module (~3000+ lines). Contains the `PreRoll` dataclass (70+ fields), `PreRollModel`, `FinishedGoodsManager`, `InventoryManager`, `WholesaleHoldsManager`, `RateCalculator`, `LearningProcessor`, `SettingsManager`, and global singletons `MODEL`, `SETTINGS`, `ANALYTICS`. |
| `database.py` | SQLite database layer (~1000+ lines). Schema creation, connection management, all CRUD operations, migration runner. Thread-local connections with WAL mode. |
| `auth_utils.py` | `PasswordManager` class with bcrypt hashing, verification, recovery key generation. Global `password_manager` instance. |
| `helpers.py` | Shared Flask helpers: `@login_required`, `@api_or_login_required` decorators, `validate_strain_data()` form validator. |
| `backup_manager.py` | `BackupScheduler` class for automated SQLite backups. AES-256-CBC encryption, GitHub Releases uploads, filesystem locks for multi-worker safety, Pushover failure notifications. |
| `config.py` | Flask configuration classes: `Config` (base), `DevelopmentConfig`, `TestingConfig`, `ProductionConfig`. |
| `centrifuge_calculator.py` | Centrifuge settings calculator for pre-roll packing optimization. |
| `_version.py` | Version string constant (`__version__`). |
| `manage.py` | Management commands (database operations, admin tasks). |
| `requirements.txt` | Python dependencies (Flask, Gunicorn, bcrypt, sentry-sdk, numpy, etc.). |
| `requirements_server.txt` | Server-only dependencies. |
| `.env` | Environment variables (SECRET_KEY, SENTRY_DSN, ADMIN_PASSWORD_HASH, BACKUP_ENCRYPTION_KEY). Not in source control. |

### Blueprints Directory (`blueprints/`)

Each blueprint is a self-contained module handling a group of related routes.

| File | URL Prefix | Purpose |
|------|------------|---------|
| `views.py` | `/` | Serves standalone HTML pages: dashboard (`/`), archive (`/archive`), achievements, finished goods, stats, wholesale, inventory, centrifuge |
| `auth.py` | `/` | Login (`/login`), logout (`/logout`), forgot password, reset password. Serves self-contained HTML with inline login forms. |
| `admin.py` | `/admin` | Admin dashboard with batch CRUD, settings, analytics, inventory management. Server-rendered HTML pages (~11,000+ lines including embedded HTML/CSS/JS templates). |
| `api_batches.py` | `/api` | Batch CRUD API: `/api/data`, `/api/archive`, `/api/batch/<id>/counts`, `/api/batch/<id>/plan`, `/api/reorder`, `/api/update-progress/<id>` |
| `api_finished_goods.py` | `/api/finished-goods` | Finished goods CRUD: list, create, update, deduct, add, pack, history, Apex sync endpoints, calculator |
| `api_inventory.py` | `/api/inventory` | Paper inventory: get, update, settings |
| `api_wholesale.py` | `/api/wholesale` | Wholesale holds: inventory summary, create/delete hold, list holds |
| `api_centrifuge.py` | `/api/centrifuge` | Centrifuge calculations: calculate, compare, curve-data, settings-guide, impulse-calculate, target-match, batch-comparison |
| `api_snapshots.py` | `/api/snapshots` | Production snapshots: history, compare-detailed, insights, export-csv |
| `api_misc.py` | `/api` | Miscellaneous: version, backup-status, settings, api-key, audit, overview, production-history, apex-sync, pushover notifications, weight checks, centrifuge recommendations |
| `pwa.py` | `/` | PWA support: manifest.json, sw.js, icons, favicon |

### Static Files (`static/`)

| File | Purpose |
|------|---------|
| `polish-system.css` | Design system CSS framework for the dashboard UI |
| `escape-utils.js` | XSS protection utilities for safe HTML rendering |
| `toast.js` | Toast notification system |
| `version-badge.js` | Version badge display widget |

### Standalone HTML Files (Root)

These are NOT Jinja2 templates. They are complete, self-contained HTML files served via `send_file()`. Each page loads data by calling API endpoints with JavaScript.

| File | Purpose |
|------|---------|
| `stats.html` | Production statistics dashboard |
| `archive.html` | Archived batches viewer |
| `achievements.html` | Production achievement tracker |
| `finished_goods.html` | Finished goods inventory management |
| `wholesale.html` | Wholesale holds management |
| `inventory.html` | Paper/cone inventory management |
| `inventory_upload.html` | Bulk inventory upload tool |
| `centrifuge_tool.html` | Centrifuge settings calculator |
| `centrifuge_demo.html` | Centrifuge demonstration page |
| `pwa.html` | PWA installation landing page |
| `recommendations.html` | Production recommendations viewer |

### Migrations (`migrations/`)

| File | Purpose |
|------|---------|
| `versions/001_baseline.py` | Baseline schema marker (no-op) |
| `versions/002_add_check_constraints.py` | Adds CHECK constraints via table recreation |
| `versions/003_add_plan_use_grams.py` | Adds plan_use_grams column to batches |
| `migrate_settings_to_db.py` | One-time migration from settings.json to settings table |
| `migrate_password_to_bcrypt.py` | One-time migration from plaintext to bcrypt passwords |
| `add_fg_cascade.py` | Adds ON DELETE CASCADE to wholesale_holds foreign key |

### Tests (`tests/`)

| File | Purpose |
|------|---------|
| `conftest.py` | Pytest fixtures: `app`, `client`, `authenticated_client` with temp database |
| `test_allocation.py` | Allocation plan algorithm tests |
| `test_api.py` | API endpoint integration tests |
| `test_auth.py` | Authentication and authorization tests |
| `test_centrifuge_recommendations.py` | Centrifuge learning/recommendation tests |
| `test_daily_production.py` | Daily production tracking tests |
| `test_database.py` | Database CRUD operation tests |
| `test_finished_goods_package.py` | Finished goods lifecycle tests |
| `test_preroll_properties.py` | PreRoll dataclass property tests |
| `test_rate_calculator.py` | Production rate calculation tests |
| `test_serialization.py` | Data serialization/deserialization tests |
| `test_settings.py` | Settings management tests |
| `test_utils.py` | Utility function tests |

### Other Notable Files

| File | Purpose |
|------|---------|
| `pre_roll_tracker.py` | Legacy monolithic version (preserved for reference) |
| `app_monolith_backup.py` | Backup of pre-blueprint monolith |
| `deploy.sh` / `deploy_quick_wins.sh` | Deployment scripts |
| `release.sh` | Release management script |
| `setup_admin_password.py` | Admin password setup utility |
| `inventory_analyzer.py` | Inventory analysis utility |
| `backfill_weight_logs.py` | Data backfill utility for weight tracking |

## ApexAPI Directory Structure

ApexAPI is a desktop application built with customtkinter for managing Apex Trading orders, packing lists, and inventory. The project root is at `~/PycharmProjects/ApexAPI/`.

### Root-Level Files

| File | Purpose |
|------|---------|
| `apex_gui.py` | Application entry point. Creates `ModernOrderGUI` and calls `.run()`. |
| `api_client.py` | Synchronous `ApexAPIClient` class using `requests.Session`. Methods: `get_orders()`, `test_connection()`, `validate_token()`, plus inventory and product endpoints. |
| `service_container.py` | `ServiceContainer` class implementing Dependency Injection. Creates and wires all services, repositories, and background tasks. Global `service_container` instance. |
| `models.py` | Data models: `Order`, `VapeCartProduct`, `VapeCartSummary`, `EdiblesProduct`, `EdiblesSummary`, `PreRollItem`, `PreRollSummary`. Rich dataclasses with computed properties. |
| `config.py` | Configuration loading: `DEFAULT_COLUMN_MAPPINGS`, `load_config()`, `generate_config_template()`. |
| `pdf_generator.py` | Order form PDF generation using reportlab. |
| `order_form_generator.py` | Excel/PDF order form generation. |
| `build_exe.py` / `build_windows.py` | PyInstaller build scripts for creating standalone executables. |
| `apex_gui.spec` / `apex_gui_windows.spec` | PyInstaller spec files for macOS and Windows. |
| `requirements.txt` | Python dependencies. |
| `pytest.ini` | Pytest configuration with unit/integration markers. |
| `ruff.toml` | Ruff linter configuration. |
| `apex_config.json` | Application configuration (license number, printer, refresh settings). |
| `apex_config_template.json` | Template for fresh installations. |

### API Layer (`api/`)

| File | Purpose |
|------|---------|
| `async_client.py` | `AsyncApexAPIClient` using aiohttp. Async versions of all API methods with connection pooling, automatic retries, and rate limiting. |

### Cache Layer (`cache/`)

| File | Purpose |
|------|---------|
| `cache_warmer.py` | `CacheWarmer` class for intelligent background cache preloading. Configurable warming strategies per data type. Access pattern tracking and statistics. |
| `batch_mapping_cache.json` | Persistent cache of METRC-to-product mappings. |
| `inventory_cache.json` | Persistent cache of inventory data. |

### Events Layer (`events/`)

| File | Purpose |
|------|---------|
| `event_bus.py` | Thread-safe publish-subscribe `EventBus` (singleton). `Event` dataclass, `EventSubscription` with priority and one-shot support, statistics tracking, and `wait_for_event()` synchronization. |
| `event_types.py` | `EventType` enum with 40+ event types across categories: orders, API, printing, configuration, UI, cache, auto-refresh, system, database, security, inventory sync. |

### GUI Layer (`gui/`)

| File | Purpose |
|------|---------|
| `main_gui.py` | `ModernOrderGUI` main window class. Order list display, toolbar, search, filtering, auto-refresh, Google Sheets sync, printing. ~2000+ lines. |
| `pre_roll_packing_list.py` | Pre-roll packing list dialog. Shows orders grouped by store/product with pack tracking, batch matching, and dashboard sync. |
| `vape_cart_fill_list.py` | Vape cartridge fill list dialog. Summarizes vape cart orders by type/size. |
| `edibles_sellthrough_gui.py` | Edibles sell-through analysis dialog. Displays sales velocity, production recommendations, pack distribution. |
| `inventory_management_gui.py` | Inventory management dialog. Tracks inventory levels across products. |
| `order_form_gui.py` | Order form generation dialog. Creates PDF/Excel order forms. |
| `store_management_dialog.py` | Store management dialog. Manages store configurations and delivery preferences. |
| `styles.py` | Shared styling constants: `COLORS`, `SPACING`, `FONTS`, `COLUMN_CONFIG`. Custom widget classes: `DropdownButton`, toolbar/icon button factories. |
| `widgets/autocomplete_entry.py` | Custom autocomplete entry widget. |

### Services Layer (`services/`)

| File | Purpose |
|------|---------|
| `order_service.py` | `OrderService` -- Core order business logic: fetch, filter, sort, third-party detection. |
| `async_order_service.py` | `AsyncOrderService` -- Async order operations with event publishing. |
| `config_service.py` | `ConfigService` -- Configuration management with `SecureConfigManager` integration, API timestamp tracking. |
| `cache_service.py` | `CacheService` -- Multi-level caching with TTL, memory/disk tiers, statistics. |
| `cache_logger.py` | `CacheLogger` -- Cache performance monitoring and reporting. |
| `print_service.py` | `PrintService` -- PDF generation and platform-specific printing (Win32 and macOS). |
| `pre_roll_service.py` | `PreRollService` -- Pre-roll order processing, product parsing, batch matching. |
| `preroll_product_parser.py` | Product name parser. Extracts strain, size, pack count from product names like "MoM - Blue Dream 0.8g CannaDart 6-Pack". |
| `preroll_sync_service.py` | `PreRollSyncService` -- Sync packed quantities to PreRollTracker dashboard. |
| `batch_mapping_service.py` | `BatchMappingService` -- Maps Apex product names to METRC numbers via PreRollTracker API. |
| `batch_inventory_sync_service.py` | `BatchInventorySyncService` -- Automated inventory synchronization between Apex and PreRollTracker. |
| `order_completion_service.py` | `OrderCompletionService` -- Handles order completion workflow and archival. |
| `delivery_sheet_service.py` | `DeliverySheetService` -- Generates delivery sheets for drivers. |
| `dashboard_api_client.py` | `DashboardAPIClient` -- HTTP client for PreRollTracker's REST API. |
| `inventory_service.py` | `InventoryService` -- Local inventory tracking and management. |
| `vape_cart_service.py` | `VapeCartService` -- Vape cartridge order processing and fill list generation. |
| `edibles_service.py` | `EdiblesService` -- Edibles order analysis, production velocity, kitchen recommendations. |
| `pack_conversion_service.py` | `PackConversionService` -- Converts between retail packs and production equivalents. |
| `google_sheets_client.py` | `GoogleSheetsClient` -- Google Sheets API integration with `GoogleSheetsConfig`. |
| `google_sheets_sync_service.py` | `GoogleSheetsSyncService` -- Bidirectional sync of packing data with Google Sheets. |
| `store_management_service.py` | `StoreManagementService` -- Store configuration and delivery preferences. |
| `product_family_service.py` | `ProductFamilyService` -- Groups products into families for analysis. |
| `product_name_suggestion_service.py` | Product name autocomplete suggestions. |
| `product_suggestion_service.py` | Product suggestion engine. |
| `production_analyzer.py` | `ProductionAnalyzer` -- Production efficiency analysis. |

### Repositories Layer (`repositories/`)

| File | Purpose |
|------|---------|
| `base_repository.py` | `BaseRepository` abstract class. Connection management (context manager), CRUD helpers (`execute_query`, `execute_update`, `execute_insert`, `execute_batch`), migration framework, backup/restore, vacuum, stats. |
| `order_repository.py` | `OrderRepository` -- Tables: `orders`, `print_status`, `order_cache_metadata`, `order_status_history`. Order CRUD, print tracking, status history. |
| `config_repository.py` | `ConfigRepository` -- Tables: `config`, `user_preferences`, `config_history`, `system_settings`. Key-value config with audit trail. |
| `preroll_repository.py` | `PreRollRepository` -- Tables: `preroll_items`, `preroll_metadata`, `preroll_items_archive`. Packing list persistence and archival. |
| `edibles_repository.py` | `EdiblesRepository` -- Tables: `edibles_orders`, `edibles_products`, `production_metrics`, `kitchen_recommendations`. Edibles sell-through analytics. |

### Security Layer (`security/`)

| File | Purpose |
|------|---------|
| `secure_config.py` | `SecureConfigManager` -- API token storage via OS keyring with JSON fallback. Token migration from JSON to keyring. Config file management excluding sensitive data. |

### PDF Generators (`pdf_generators/`)

| File | Purpose |
|------|---------|
| `edibles_pdf.py` | Edibles-specific PDF report generation. |
| `vape_cart_pdf.py` | Vape cartridge fill list PDF generation. |

### Tests (`tests/`)

**Unit Tests** (`tests/unit/`):

| File | Tests |
|------|-------|
| `test_api_client.py` | ApexAPIClient method tests |
| `test_async_client.py` | AsyncApexAPIClient tests |
| `test_batch_mapping_service.py` | METRC mapping logic |
| `test_cache_logger.py` | Cache logging tests |
| `test_cache_service.py` | Cache TTL, eviction tests |
| `test_config_service.py` | Config loading/saving |
| `test_dashboard_api_client.py` | Dashboard API communication |
| `test_delivery_sheet_service.py` | Delivery sheet generation |
| `test_edibles_service.py` | Edibles analysis logic |
| `test_event_bus.py` | EventBus pub/sub tests |
| `test_google_sheets_client.py` | Google Sheets API tests |
| `test_google_sheets_sync_service.py` | Sheets sync logic |
| `test_inventory_service.py` | Inventory management |
| `test_models.py` | Data model property tests |
| `test_order_completion_service.py` | Order completion workflow |
| `test_order_service.py` | Order business logic |
| `test_pack_conversion_service.py` | Pack conversion math |
| `test_pre_roll_service.py` | Pre-roll processing |
| `test_preroll_key_matching.py` | Product-to-METRC matching |
| `test_preroll_product_parser.py` | Product name parsing |
| `test_print_service.py` | PDF generation/printing |
| `test_product_family_service.py` | Product grouping |
| `test_production_analyzer.py` | Production analysis |
| `test_secure_config.py` | Keyring/config security |
| `test_service_container.py` | DI container lifecycle |
| `test_store_management_service.py` | Store management |
| `test_vape_cart_service.py` | Vape cart processing |

**Integration Tests** (`tests/integration/`):

| File | Tests |
|------|-------|
| `test_base_repository.py` | Base repository database operations |
| `test_config_repository.py` | Config repository with real SQLite |
| `test_edibles_repository.py` | Edibles repository with real SQLite |
| `test_order_repository.py` | Order repository with real SQLite |
| `test_preroll_repository.py` | Preroll repository with real SQLite |

## Module Responsibilities and Dependencies

### PreRollTracker Dependency Graph

```
app.py
  +--- Flask, Flask-Limiter, Flask-WTF, Sentry SDK
  +--- blueprints/* (all 11 blueprints)
  +--- backup_manager.py
  +--- tracker_core.py (learning processor thread)
  +--- _version.py

blueprints/api_*.py, admin.py
  +--- helpers.py (@login_required, @api_or_login_required)
  +--- tracker_core.py (MODEL, SETTINGS, managers)

tracker_core.py
  +--- database.py (all CRUD functions)
  +--- numpy (optional, for regression)

database.py
  +--- sqlite3 (standard library)
  +--- migrations/versions/* (auto-applied)

auth_utils.py
  +--- bcrypt
  +--- tracker_core.SETTINGS (for legacy password fallback)

backup_manager.py
  +--- subprocess (openssl for encryption, gh for GitHub releases)
  +--- fcntl (Unix worker election)
```

### ApexAPI Dependency Graph

```
apex_gui.py
  +--- gui/main_gui.py

gui/main_gui.py
  +--- service_container.service_container
  +--- events.EventType
  +--- models.Order
  +--- services/google_sheets_client.py
  +--- services/google_sheets_sync_service.py
  +--- gui/styles.py

service_container.py
  +--- api_client.ApexAPIClient
  +--- api/async_client.AsyncApexAPIClient
  +--- cache/cache_warmer.CacheWarmer
  +--- events/event_bus.EventBus
  +--- repositories/* (OrderRepository, ConfigRepository, PreRollRepository)
  +--- services/* (OrderService, CacheService, ConfigService, PrintService, etc.)

services/*
  +--- api_client.py or api/async_client.py (for API calls)
  +--- repositories/* (for database access)
  +--- events/event_bus.py (for publishing events)
  +--- models.py (for data structures)

repositories/*
  +--- base_repository.BaseRepository
  +--- sqlite3 (via base class)
```

## Key Classes and Methods

### PreRollTracker Key Classes

**PreRoll** (`tracker_core.py`) -- Dataclass representing a production batch with 70+ fields. Key computed properties:

- `total_pre_rolls` -- Sum of all size counts
- `calculated_grams_used` -- Auto-calculated from counts
- `yield_percent` -- Production yield percentage
- `grind_progress_percent` / `grind_remaining` -- Grinding progress
- `labels_needed` / `labels_progress_percent` -- Label tracking
- `total_packaged` / `packaging_balance` / `packaging_complete` -- Packaging tracking

**PreRollModel** (`tracker_core.py`) -- Main data access class wrapping database operations. Key methods:

- `get_active_batches()` / `get_archived_batches()` -- Retrieve batches
- `get_active_as_dict()` -- Serialize active batches for API
- `add_batch()` / `update_batch()` / `delete_batch()` -- CRUD
- `archive_batch()` / `unarchive_batch()` -- Archival

**FinishedGoodsManager** (`tracker_core.py`, ~2,000 lines) -- Manages METRC packages, inventory operations, Apex integration, and wholesale holds. This is one of the largest managers in the codebase.

*Package CRUD:*
- `add_package(metrc_number, strain, grams, ...)` -- Create new METRC package
- `get_package(metrc_number)` / `get_all_packages(include_archived)` / `get_active_packages()` -- Retrieve packages
- `update_package(metrc_number, field, value, reason)` -- Update editable fields (strain, notes, source_batch_id)
- `delete_package(metrc_number)` -- Permanent deletion (cascades to wholesale_holds)
- `search_packages(query)` -- Search by METRC number or strain name

*Inventory Operations:*
- `deduct_inventory(metrc_number, grams, units, unit_size, reason)` -- Remove inventory by grams or by unit count (calculates grams from unit_size)
- `add_inventory(metrc_number, grams, units, unit_size, reason)` -- Add inventory
- `set_physical_override(metrc_number, physical_grams, reason)` -- Override calculated grams with physical count (set to None to clear)

*Order Lifecycle:*
- `place_order(metrc_number, grams)` -- Reserve grams for an order (doesn't reduce current_grams)
- `set_ordered(metrc_number, grams)` / `set_packed(metrc_number, grams)` -- Set total ordered/packed amounts directly
- `sync_package(metrc_number, ordered_grams, packed_grams)` -- Atomically sync both ordered and packed
- `pack_order(metrc_number, grams)` -- Pack order (reduces current_grams)
- `complete_order(metrc_number, grams, order_id)` -- Fulfill order permanently (deducts from current_grams, adds to grams_fulfilled)

*Apex Integration:*
- `set_apex_auto_inventory(metrc_number, enabled)` -- Enable/disable auto-sync to Apex Trading
- `set_apex_units(metrc_number, singles_0_5g, singles_1g, ...)` -- Set unit counts directly
- `calculate_apex_units(metrc_number, held_quantities)` -- Calculate available units from grams, subtracting wholesale holds, applying SKU settings
- `set_apex_sku_settings(metrc_number, sku_settings, auto_calculate)` -- Configure per-SKU exclusions and manual overrides
- `decrement_apex_manual_units(metrc_number, sku, units, idempotency_key)` -- Idempotent decrement when Apex reports sales. Uses `processed_decrements` JSON field for deduplication.

*Custom SKUs:*
- `get_custom_skus(metrc_number)` / `set_custom_skus(metrc_number, custom_skus)` -- Get/replace all custom SKU definitions
- `add_custom_sku(metrc_number, sku_key, sku_def)` / `remove_custom_sku(metrc_number, sku_key)` -- Add/remove individual custom SKUs

*Archive Management:*
- `archive_package(metrc_number)` / `restore_package(metrc_number)` / `orphan_package(metrc_number)` -- Status transitions

*History & Reporting:*
- `get_package_history(metrc_number)` / `get_all_history(limit)` -- Retrieve change history
- `get_summary()` -- Dashboard summary statistics (total packages, active count, grams available, etc.)
- `check_low_stock_alerts()` / `send_stock_alerts()` -- Pushover alerting for low-stock packages

**WholesaleHoldsManager** (`tracker_core.py`) -- Manages inventory reservations for wholesale orders:

- `create_hold(metrc_number, sku_name, quantity, notes)` -- Reserve units from a METRC package
- `get_all_holds()` / `get_holds_for_package(metrc_number)` -- Retrieve holds
- `get_held_quantities()` -- Returns dict of {metrc_number: {sku_name: total_held}} used by `calculate_apex_units()`
- `remove_hold(hold_id)` -- Release a hold
- `get_wholesale_inventory()` -- Build wholesale-friendly view grouped by strain

**Key Algorithm: `calculate_apex_units()`**

This is the critical algorithm that determines what stores see in Apex Trading:

1. Get effective grams (physical_override or current_grams)
2. Subtract grams_ordered + grams_packed + grams_fulfilled
3. Get held quantities from wholesale_holds for this package
4. For each SKU type (default + custom):
   - If excluded in settings: set to 0
   - If manual_units set: use that value, subtract any held quantity
   - Otherwise: divide available grams by grams_per_unit, subtract held quantity
5. Return unit counts per SKU

**Frontend: `finished_goods.html`**

The Finished Goods page is a self-contained HTML file (not a Jinja2 template). It uses vanilla JavaScript to:
- Poll `/api/finished-goods/last-updated` every few seconds for change detection
- Render package cards with summary stats, grams bars, order tracking, and APEX inventory
- Handle all CRUD modals (add, edit, deduct, add, physical override, Apex settings, custom SKUs)
- Manage search/filter state client-side

**SettingsManager** (`tracker_core.py`) -- Key-value settings with typed accessors. Key methods:

- `api_key()` / `admin_password()` -- Security settings
- `get()` / `set()` -- Generic key-value access

**RateCalculator** (`tracker_core.py`) -- Production rate computation using session-based tracking. Supports rate history, smoothed rates, trend analysis.

**LearningProcessor** (`tracker_core.py`) -- Machine learning for centrifuge recommendations. Processes completed batch outcomes to improve future suggestions.

### ApexAPI Key Classes

**ServiceContainer** (`service_container.py`) -- Dependency injection container. Key methods:

- `initialize()` -- Creates all services in dependency order
- `get_*_service()` / `get_*_repository()` -- Typed service accessors
- `shutdown()` -- Graceful cleanup of all services
- `reconfigure_service()` -- Runtime reconfiguration

**EventBus** (`events/event_bus.py`) -- Thread-safe singleton pub/sub. Key methods:

- `subscribe(event_type, callback, priority, once)` -- Register handler
- `publish(event_type, data, source)` -- Emit event
- `wait_for_event(event_type, timeout)` -- Synchronous wait
- `get_stats()` -- Performance metrics

**BaseRepository** (`repositories/base_repository.py`) -- Abstract base with common DB operations. Key methods:

- `get_connection()` -- Context manager for connections
- `get_transaction()` -- Context manager with auto-commit/rollback
- `execute_query()` / `execute_update()` / `execute_insert()` -- Query helpers
- `backup_database()` / `restore_database()` -- Backup support

**CacheWarmer** (`cache/cache_warmer.py`) -- Intelligent cache preloading. Key methods:

- `run_warming_cycle()` -- Execute one warming pass
- `schedule_warming(interval_minutes)` -- Periodic warming
- `configure_from_dict()` -- Runtime configuration

## Design Patterns

### Blueprint Pattern (PreRollTracker)

Flask blueprints organize routes by domain concern. Each blueprint registers its routes with a URL prefix and can be independently developed and tested. The 11 blueprints separate views (HTML serving), authentication, admin (server-rendered pages), and API routes by resource type.

### Service Container / Dependency Injection (ApexAPI)

The `ServiceContainer` creates all services with their dependencies explicitly wired. Services receive their dependencies through constructor parameters rather than importing globals. This enables testing with mocked dependencies and clear initialization order.

### Repository Pattern (ApexAPI)

`BaseRepository` provides a consistent data access interface with connection management. Each concrete repository (Order, Config, PreRoll, Edibles) defines its own tables and migrations while inheriting common operations. The repository abstracts SQLite details from service code.

### Observer / Event Bus Pattern (ApexAPI)

The `EventBus` implements publish-subscribe communication. Components publish events (like `ORDERS_LOADED` or `CONFIG_CHANGED`) and other components subscribe to react. This decouples the GUI from services and services from each other.

### Dataclass as Domain Model (Both)

Both projects use Python dataclasses as rich domain models. `PreRoll` (PreRollTracker) and `Order`/`PreRollItem`/`EdiblesProduct` (ApexAPI) include computed properties that derive values from stored fields.

### Thread-Local Storage (PreRollTracker)

`database.py` uses `threading.local()` for per-thread SQLite connections. This avoids SQLite's threading limitations while allowing concurrent request handling in Gunicorn workers.

### Singleton Pattern (ApexAPI)

The `EventBus` uses a thread-safe singleton (`__new__` with double-checked locking). The global `service_container` instance provides a single point of service access.

## Where to Find Things

| If you need to... | Look in... |
|-------------------|-----------|
| Add a new API endpoint to PreRollTracker | `blueprints/api_*.py` (choose the appropriate resource) |
| Add a new production batch field | `tracker_core.py::PreRoll` dataclass, `database.py::init_db()` schema, `database.py::_preroll_to_row()` and `_row_to_preroll()` |
| Change authentication logic | `helpers.py` (decorators), `auth_utils.py` (password handling), `blueprints/auth.py` (routes) |
| Modify the dashboard UI | Root HTML files (e.g., `stats.html`, `finished_goods.html`), `static/polish-system.css` |
| Add a new admin page | `blueprints/admin.py` (routes and embedded HTML templates) |
| Change database schema | `database.py::init_db()` for new tables/columns, create new migration in `migrations/versions/` |
| Add a new GUI module to ApexAPI | Create file in `gui/`, register in `gui/main_gui.py`, add service dependencies to `service_container.py` |
| Add a new ApexAPI service | Create file in `services/`, add initialization to `ServiceContainer.initialize()`, wire dependencies |
| Add a new database table to ApexAPI | Add to appropriate repository's `create_tables()` method, or create new repository |
| Change how Apex API is called | `api_client.py` (sync), `api/async_client.py` (async) |
| Modify cache behavior | `services/cache_service.py` (service), `cache/cache_warmer.py` (warming), `service_container.py` (configuration) |
| Add a new event type | `events/event_types.py::EventType` enum, subscribe in `service_container.py::_setup_event_subscriptions()` |
| Change backup behavior | `backup_manager.py` (PreRollTracker), `repositories/base_repository.py::backup_database()` (ApexAPI) |
| Debug production rates | `tracker_core.py::RateCalculator`, batch `rate_history` and `rate_metrics` JSON fields |
| Understand METRC integration | `finished_goods` table schema, `services/batch_mapping_service.py`, `services/batch_inventory_sync_service.py` |
| Configure pre-roll product parsing | `services/preroll_product_parser.py` (ApexAPI) |
| Add Google Sheets integration | `services/google_sheets_client.py`, `services/google_sheets_sync_service.py` |
| Build a standalone executable | `build_exe.py`, `apex_gui.spec` (macOS), `apex_gui_windows.spec` (Windows) |
| Add a new test | `tests/` directory in either project, following existing patterns |
