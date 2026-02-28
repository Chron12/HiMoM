# Testing Guide

## Overview

Both PreRollTracker and ApexAPI use pytest as their test framework. PreRollTracker has 13 test files covering API, authentication, database, and business logic. ApexAPI has 27+ unit test files and 5 integration test files with clear separation between fast unit tests and database-backed integration tests.

## PreRollTracker Test Suite

### Test Directory Structure

```
tests/
    conftest.py                          # Shared fixtures
    test_allocation.py                   # Allocation plan algorithm
    test_api.py                          # API endpoint integration tests
    test_auth.py                         # Authentication and authorization
    test_centrifuge_recommendations.py   # Centrifuge learning engine
    test_daily_production.py             # Daily production tracking
    test_database.py                     # Database CRUD operations
    test_finished_goods_package.py       # Finished goods lifecycle
    test_preroll_properties.py           # PreRoll dataclass properties
    test_rate_calculator.py              # Production rate calculations
    test_serialization.py               # Data serialization roundtrips
    test_settings.py                     # Settings management
    test_utils.py                        # Utility function tests
```

There are also root-level test files for specific security and concurrency concerns:

```
test_app.py                              # Basic app smoke tests
test_csrf_protection.py                  # CSRF token validation
test_xss_protection.py                   # XSS sanitization
test_rate_limiting.py                    # Flask-Limiter rate limiting
test_cache_staleness.py                  # Cache freshness tests
test_inventory_race_condition.py         # Concurrent inventory updates
test_demonstrate_race_fix.py             # Race condition fix verification
test_settings_race_conditions.py         # Settings concurrency
test_settings_concurrency.py             # Settings thread safety
test_quick_win_fixes.py                  # Targeted regression tests
```

### conftest.py Fixtures

The `conftest.py` file provides the foundational fixtures for all PreRollTracker tests.

**Environment Setup**

Before any imports, the conftest sets critical environment variables:

```python
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest")
os.environ.setdefault("SENTRY_DSN", "")           # disable Sentry
os.environ.setdefault("FLASK_ENV", "testing")
```

It also initializes the default database so that module-level imports in `tracker_core.py` (which queries the database at import time) do not crash during test collection.

**Core Fixtures**

| Fixture | Scope | Description |
|---------|-------|-------------|
| `app` | function | Yields the Flask app configured for testing. Creates a fresh temporary database via `tmp_path`, monkeypatches `database.DEFAULT_DB_PATH` to point to it, initializes the schema, and disables CSRF. Each test gets a completely isolated database. |
| `client` | function | Flask test client from `app.test_client()`. Used for making HTTP requests in tests. |
| `runner` | function | Flask CLI test runner from `app.test_cli_runner()`. |
| `authenticated_client` | function | A test client with `session["logged_in"] = True` injected. Bypasses the login flow for testing authenticated endpoints. |

**How Database Isolation Works**

```python
@pytest.fixture()
def app(tmp_path, monkeypatch):
    test_db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(database, "DEFAULT_DB_PATH", test_db_path)
    init_db(test_db_path)
    close_connection()  # Force fresh connections with new path
    # ... yield app ...
    close_connection(test_db_path)
    close_connection()
```

This ensures:

1. Every test uses a unique temporary SQLite file
2. The global `DEFAULT_DB_PATH` is redirected so all `get_connection()` calls hit the test DB
3. Thread-local connections are reset between tests
4. The temp directory is automatically cleaned up by pytest

### Test Categories

#### Allocation Tests (`test_allocation.py`)

Tests the `calculate_allocation_plan()` function which determines how many pre-rolls of each size to produce from a given amount of material.

Key test scenarios:

- Basic allocation with single size
- Multi-size allocation with material constraints
- Edge cases: zero material, zero target, maximum allocation
- Plan-use-grams limiting (partial material usage)
- Rounding behavior to prevent fractional pre-rolls

#### API Tests (`test_api.py`)

Integration tests that exercise API endpoints through the Flask test client.

Key test scenarios:

- `GET /api/data` returns active batches
- `POST /api/batch/<id>/counts` updates production counts
- `POST /api/batch/<id>/plan` sets planned quantities
- `POST /api/archive/<id>` archives a batch
- `GET /api/overview` returns dashboard summary
- Authentication enforcement on protected endpoints
- Error handling for invalid inputs and missing batches
- JSON response structure validation

Example pattern:

```python
def test_api_data_returns_active_batches(authenticated_client, app):
    # Setup: create a batch through the model
    from tracker_core import MODEL
    MODEL.add_batch(strain="Test Strain", input_grams=100, target_grams_each=0.5)

    # Exercise: call the API
    response = authenticated_client.get("/api/data")

    # Verify
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["strain"] == "Test Strain"
```

#### Auth Tests (`test_auth.py`)

Tests authentication and authorization behavior.

Key test scenarios:

- Login with correct/incorrect password
- Session persistence after login
- Logout clears session
- Protected routes redirect to login when unauthenticated
- API key authentication via X-API-Key header
- Constant-time comparison for API keys
- Password hashing and verification roundtrips
- Recovery key generation and verification

#### Centrifuge Recommendation Tests (`test_centrifuge_recommendations.py`)

Tests the machine learning-based centrifuge recommendation engine.

Key test scenarios:

- Recommendation generation from historical batch data
- Learning from completed batch outcomes
- Fill gauge suggestions based on weight measurements
- Strain-specific recommendation profiles
- Handling of insufficient data

#### Daily Production Tests (`test_daily_production.py`)

Tests production tracking over time.

Key test scenarios:

- Production session start/stop/pause
- Duration calculations across multiple sessions
- Rate calculation during active sessions
- Stage transitions and their effect on timing

#### Database Tests (`test_database.py`)

Low-level tests for database.py CRUD operations.

Key test scenarios:

- `init_db()` creates all tables and indexes
- `save_batch()` / `get_batch()` roundtrip
- `get_all_batches()` filtering by archived status
- `save_finished_good()` / `get_finished_good()` roundtrip
- `log_audit()` creates audit entries
- `save_inventory_item()` / `get_inventory()` roundtrip
- `log_inventory_usage()` tracking
- Transaction management: `begin_exclusive_transaction()`, `commit_transaction()`, `rollback_transaction()`
- Concurrent access behavior

#### Finished Goods Tests (`test_finished_goods_package.py`)

Tests the finished goods lifecycle from creation through depletion.

Key test scenarios:

- Creating a finished goods package with METRC number
- Deducting grams (order fulfillment)
- Adding grams (inventory correction)
- Status transitions (active -> depleted)
- History entry creation on each change
- Wholesale holds preventing over-deduction
- Cascade delete of holds when package is removed

#### PreRoll Property Tests (`test_preroll_properties.py`)

Tests computed properties on the PreRoll dataclass.

Key test scenarios:

- `total_pre_rolls` sums all size counts
- `calculated_grams_used` computes weight from counts
- `yield_percent` handles zero input
- `grind_progress_percent` clamps to 0-100%
- `labels_needed` matches planned counts
- `packaging_balance` and `packaging_complete` checks
- Source strain names for infused products

#### Rate Calculator Tests (`test_rate_calculator.py`)

Tests production rate computation.

Key test scenarios:

- Simple rate: pre-rolls / hours
- Session-based rate with multiple work sessions
- Smoothed rate with exponential weighting
- Trend detection (increasing, decreasing, stable)
- Confidence scoring based on data quantity
- Edge cases: single session, very short sessions

#### Serialization Tests (`test_serialization.py`)

Tests data conversion between Python objects and database/JSON formats.

Key test scenarios:

- `_preroll_to_row()` converts all fields correctly
- `_row_to_preroll()` reconstructs from database row
- Boolean fields stored as integers (0/1)
- JSON fields (lists, dicts) serialized as TEXT
- Roundtrip: PreRoll -> row -> PreRoll preserves all data
- Handling of None/null values
- Backward compatibility with missing columns

#### Settings Tests (`test_settings.py`)

Tests the SettingsManager key-value store.

Key test scenarios:

- Get/set string, integer, boolean, JSON values
- Default values for missing keys
- API key retrieval and regeneration
- Admin password access
- Concurrent settings access

#### Utils Tests (`test_utils.py`)

Tests utility functions.

Key test scenarios:

- `normalize_size()` handles all input formats
- `safe_datetime_parse()` handles ISO variants
- `utc_to_local_display()` timezone conversion
- `clamp_fill_gauge()` range enforcement

### Running Specific PreRollTracker Tests

```bash
# All tests
cd ~/PycharmProjects/PreRollTracker
pytest

# Single file
pytest tests/test_database.py

# Single test function
pytest tests/test_database.py::test_save_and_get_batch

# Pattern match
pytest -k "test_api"

# Verbose with full tracebacks
pytest -v --tb=long

# Stop on first failure
pytest -x

# Show print output
pytest -s

# With coverage report
pytest --cov=. --cov-report=html --cov-report=term-missing

# Exclude slow tests (if marked)
pytest -m "not slow"
```

## ApexAPI Test Suite

### Test Directory Structure

```
tests/
    __init__.py
    conftest.py                              # Shared fixtures
    unit/
        __init__.py
        test_api_client.py                   # ApexAPIClient tests
        test_async_client.py                 # AsyncApexAPIClient tests
        test_batch_mapping_service.py        # METRC mapping tests
        test_cache_logger.py                 # Cache logging tests
        test_cache_service.py                # Cache TTL/eviction tests
        test_config_service.py               # Config management tests
        test_dashboard_api_client.py         # Dashboard API tests
        test_delivery_sheet_service.py       # Delivery sheet tests
        test_edibles_service.py              # Edibles analysis tests
        test_event_bus.py                    # EventBus pub/sub tests
        test_google_sheets_client.py         # Google Sheets API tests
        test_google_sheets_sync_service.py   # Sheets sync tests
        test_inventory_service.py            # Inventory tests
        test_models.py                       # Data model tests
        test_order_completion_service.py     # Order completion tests
        test_order_service.py                # Order logic tests
        test_pack_conversion_service.py      # Pack math tests
        test_pre_roll_service.py             # Pre-roll processing tests
        test_preroll_key_matching.py         # Product matching tests
        test_preroll_product_parser.py       # Name parsing tests
        test_print_service.py               # Print/PDF tests
        test_product_family_service.py       # Product grouping tests
        test_production_analyzer.py          # Analysis tests
        test_secure_config.py                # Security tests
        test_service_container.py            # DI container tests
        test_store_management_service.py     # Store config tests
        test_vape_cart_service.py            # Vape cart tests
    integration/
        __init__.py
        test_base_repository.py              # Base DB operations
        test_config_repository.py            # Config DB operations
        test_edibles_repository.py           # Edibles DB operations
        test_order_repository.py             # Order DB operations
        test_preroll_repository.py           # Preroll DB operations
```

### conftest.py Fixtures

ApexAPI's conftest provides reusable test data:

| Fixture | Description |
|---------|-------------|
| `sample_preroll_item` | A `PreRollItem` with realistic data: "MoM - Blue Dream Infused 0.8g CannaDart 6-Pack", 100 ordered, 35 packed |
| `sample_order` | An `Order` with typical values: Pending status, Portland OR, 5 items |
| `in_memory_db` | A `PreRollRepository` backed by a temporary SQLite database in `tmp_path` |

The conftest also adds the project root to `sys.path` for imports.

### Test Patterns and Techniques

#### Unit Test Pattern

Unit tests mock all external dependencies:

```python
from unittest.mock import MagicMock, patch

def test_order_service_fetches_orders():
    # Create mock API client
    mock_api_client = MagicMock()
    mock_api_client.get_orders.return_value = {
        "success": True,
        "data": [{"id": 1, "order_status": "Pending", ...}]
    }

    # Create service with mock
    service = OrderService(mock_api_client)

    # Exercise
    orders = service.get_pending_orders()

    # Verify
    assert len(orders) == 1
    mock_api_client.get_orders.assert_called_once()
```

#### Mocking API Calls

For HTTP-level mocking, ApexAPI uses the `responses` library:

```python
import responses

@responses.activate
def test_api_client_get_orders():
    responses.add(
        responses.GET,
        "https://app.apextrading.com/api/v1/receiving-orders",
        json={"data": [{"id": 1}]},
        status=200,
    )

    client = ApexAPIClient()
    client.set_token("test-token")
    result = client.get_orders()

    assert result["success"] is True
    assert len(result["data"]) == 1
```

#### Integration Test Pattern

Integration tests use real SQLite databases:

```python
import pytest
from repositories.order_repository import OrderRepository

@pytest.fixture
def order_repo(tmp_path):
    db_path = str(tmp_path / "test.db")
    return OrderRepository(db_path=db_path)

def test_save_and_retrieve_order(order_repo):
    # Insert
    order_repo.save_order({
        "id": 1,
        "uuid": "test-uuid",
        "invoice_number": "INV-001",
        "order_status": "Pending",
        ...
    })

    # Retrieve
    order = order_repo.get_order(1)
    assert order is not None
    assert order["invoice_number"] == "INV-001"
```

#### EventBus Testing

The EventBus singleton requires special handling in tests:

```python
def test_event_publishing():
    from events.event_bus import EventBus
    from events import EventType

    bus = EventBus()
    received_events = []

    def handler(event):
        received_events.append(event)

    bus.subscribe(EventType.ORDERS_LOADED, handler)
    bus.publish(EventType.ORDERS_LOADED, {"count": 5})

    assert len(received_events) == 1
    assert received_events[0].data["count"] == 5

    # Cleanup
    bus.clear_all_subscriptions()
```

### Key Test Files Explained

#### test_preroll_product_parser.py

Tests the product name parser which extracts structured data from Apex Trading product names.

```
Input:  "MoM - Blue Dream Infused 0.8g CannaDart 6-Pack"
Output: strain="Blue Dream Infused", unit_size=0.8, pack_count=6
```

Key test scenarios:

- Standard product names with strain, size, and pack count
- Single units (no pack suffix)
- Various size formats: "0.5g", "0.8g", "1g"
- Infused product names
- Names with special characters or HTML entities
- Names without recognizable patterns (fallback behavior)

#### test_service_container.py

Tests the dependency injection container lifecycle.

Key test scenarios:

- `initialize()` creates all services
- Services are accessible via typed getters
- `shutdown()` cleans up all resources
- Double initialization is idempotent
- Service reconfiguration at runtime

#### test_cache_service.py

Tests cache behavior with TTL expiration and multiple cache categories.

Key test scenarios:

- Cache set/get with TTL
- Cache expiration after TTL
- Cache clear by category
- Cache statistics tracking
- Memory cache vs disk cache fallback

#### test_pack_conversion_service.py

Tests the conversion between retail packs and production equivalents for edibles.

Key test scenarios:

- 100mg 10-pack to individual unit conversion
- Pack type detection from product names
- Production batch allocation calculations
- Edge cases: unknown pack sizes, zero quantities

### Running Specific ApexAPI Tests

```bash
# All tests
cd ~/PycharmProjects/ApexAPI
pytest

# Unit tests only (fast)
pytest -m unit

# Integration tests only
pytest -m integration

# Specific test file
pytest tests/unit/test_order_service.py

# Specific test class
pytest tests/unit/test_models.py::TestPreRollItem

# Specific test function
pytest tests/unit/test_models.py::TestPreRollItem::test_remaining_calculation

# Pattern match
pytest -k "test_cache"

# Verbose output
pytest -v --tb=short

# With coverage
pytest --cov=. --cov-report=html

# Parallel execution (requires pytest-xdist)
pytest -n auto
```

## Writing New Tests

### For PreRollTracker

1. **Determine the test type:**

   - Testing a database operation? Add to `tests/test_database.py`
   - Testing an API endpoint? Add to `tests/test_api.py`
   - Testing business logic? Add to the relevant `tests/test_*.py` file
   - Testing a new feature? Create a new test file in `tests/`

2. **Use the right fixtures:**

   ```python
   def test_something(app):
       """Use 'app' for database-only tests."""
       from tracker_core import MODEL
       MODEL.add_batch(...)

   def test_api_endpoint(authenticated_client, app):
       """Use 'authenticated_client' for testing auth-required endpoints."""
       response = authenticated_client.get("/api/data")

   def test_public_endpoint(client, app):
       """Use 'client' for testing public endpoints."""
       response = client.get("/api/version")
   ```

3. **Follow the Arrange-Act-Assert pattern:**

   ```python
   def test_batch_archival(authenticated_client, app):
       # Arrange: create a batch
       from tracker_core import MODEL
       batch_id = MODEL.add_batch(strain="Test", input_grams=100, target_grams_each=0.5)

       # Act: archive it
       response = authenticated_client.post(f"/api/archive/{batch_id}")

       # Assert: verify the response and state change
       assert response.status_code == 200
       batch = MODEL.get_batch(batch_id)
       assert batch.archived is True
   ```

### For ApexAPI

1. **Determine the test type:**

   - Testing service logic? Create in `tests/unit/`
   - Testing database operations? Create in `tests/integration/`

2. **Mark your tests:**

   ```python
   import pytest

   @pytest.mark.unit
   def test_service_logic():
       ...

   @pytest.mark.integration
   def test_database_operation(tmp_path):
       ...
   ```

3. **Mock external dependencies in unit tests:**

   ```python
   from unittest.mock import MagicMock

   def test_new_service():
       mock_api = MagicMock()
       mock_repo = MagicMock()
       service = MyNewService(api_client=mock_api, repository=mock_repo)

       result = service.do_something()

       mock_api.some_method.assert_called_once()
   ```

4. **Use tmp_path for integration tests:**

   ```python
   def test_repository_crud(tmp_path):
       repo = MyRepository(db_path=str(tmp_path / "test.db"))
       repo.save(...)
       result = repo.get(...)
       assert result is not None
   ```

5. **Test event publishing:**

   ```python
   def test_service_publishes_event():
       mock_bus = MagicMock()
       service = MyService(event_bus=mock_bus)

       service.do_action()

       mock_bus.publish.assert_called_with(
           EventType.SOME_EVENT,
           {"key": "value"}
       )
   ```

## Test Coverage Status

### PreRollTracker Coverage

The test suite covers the core business logic extensively:

| Module | Coverage Focus |
|--------|---------------|
| `tracker_core.py` | PreRoll properties, model operations, rate calculation, allocation |
| `database.py` | All CRUD operations, schema init, migrations |
| `auth_utils.py` | Password hashing, verification, recovery keys |
| `helpers.py` | Decorators tested through API endpoint tests |
| `blueprints/api_*.py` | Key endpoints tested through `test_api.py` |
| `backup_manager.py` | Limited coverage (requires filesystem mocking) |
| `centrifuge_calculator.py` | Covered via centrifuge recommendation tests |

Areas with lower coverage:

- `blueprints/admin.py` -- Large server-rendered admin interface (11K+ lines)
- `backup_manager.py` -- External system dependencies (openssl, gh, fcntl)
- Standalone HTML files -- Not testable via pytest (would need browser testing)

### ApexAPI Coverage

The test suite is comprehensive for services and repositories:

| Module | Coverage Focus |
|--------|---------------|
| `services/` | All 25+ services have corresponding unit tests |
| `repositories/` | All 5 repositories have integration tests |
| `events/` | EventBus lifecycle, subscription, and publishing |
| `models.py` | All dataclass properties and methods |
| `api_client.py` | HTTP interactions via responses mock |
| `service_container.py` | Container lifecycle |

Areas with lower coverage:

- `gui/` modules -- GUI testing requires tkinter which is difficult to automate
- `cache/cache_warmer.py` -- Async background tasks are complex to test
- `pdf_generator.py` / `pdf_generators/` -- PDF output validation
- Build scripts (`build_exe.py`, `build_windows.py`)

## Continuous Integration Notes

### Test Isolation

Both projects ensure complete test isolation:

- **Database:** Every test gets a fresh temporary SQLite database
- **Environment:** Environment variables are set to test-safe values before imports
- **State:** Global state (thread-local connections, singletons) is reset between tests
- **Network:** No real HTTP calls in unit tests (mocked via `responses` or `unittest.mock`)

### Common Test Failures and Solutions

**"OperationalError: database is locked"**

- Cause: Thread-local connection not closed between tests
- Fix: Ensure `close_connection()` is called in fixture teardown

**"ImportError: cannot import from tracker_core"**

- Cause: Database not initialized before module-level code runs
- Fix: The conftest calls `init_db()` before imports; ensure test environment variables are set

**"EventBus has leftover subscriptions"**

- Cause: Previous test did not clean up subscriptions
- Fix: Call `bus.clear_all_subscriptions()` in fixture teardown

**"CSRF token missing"**

- Cause: Test Flask app did not disable CSRF
- Fix: Set `WTF_CSRF_ENABLED = False` in test app config

**"KeyError: 'api_token'"**

- Cause: SecureConfigManager tries to access keyring in CI
- Fix: Mock `keyring` in tests, or set `HAS_KEYRING = False`

## Advanced Testing Topics

### Testing Database Migrations (PreRollTracker)

Database migrations in PreRollTracker can be tested by applying them to a fresh database:

```python
def test_migration_002_adds_check_constraints(tmp_path):
    """Verify migration 002 adds CHECK constraints without data loss."""
    import sqlite3
    from database import init_db, get_connection, close_connection, save_batch
    import database

    db_path = str(tmp_path / "test_migration.db")

    # Initialize with full schema
    init_db(db_path)

    # Insert a batch before migration
    conn = get_connection(db_path)
    conn.execute("""
        INSERT INTO batches (id, strain, input_grams, target_grams_each)
        VALUES ('test-1', 'Test Strain', 100.0, 0.5)
    """)
    conn.commit()

    # Verify CHECK constraint works
    try:
        conn.execute("""
            INSERT INTO batches (id, strain, input_grams, target_grams_each, stage)
            VALUES ('test-2', 'Bad Stage', 100.0, 0.5, 99)
        """)
        conn.commit()
        assert False, "Should have raised IntegrityError for invalid stage"
    except sqlite3.IntegrityError:
        conn.rollback()  # Expected

    close_connection(db_path)
```

### Testing Concurrent Access (PreRollTracker)

The root-level test files like `test_inventory_race_condition.py` and `test_settings_concurrency.py` test thread safety:

```python
import threading

def test_concurrent_inventory_updates(app):
    """Verify inventory updates are thread-safe."""
    from tracker_core import INVENTORY

    errors = []
    results = []

    def update_inventory(size, count):
        try:
            INVENTORY.update_papers(size, count)
            current = INVENTORY.get_inventory()
            results.append(current)
        except Exception as e:
            errors.append(str(e))

    threads = [
        threading.Thread(target=update_inventory, args=("0_5", 10)),
        threading.Thread(target=update_inventory, args=("0_7", 20)),
        threading.Thread(target=update_inventory, args=("1_0", 30)),
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Concurrent errors: {errors}"
```

### Testing Async Services (ApexAPI)

Testing async code in ApexAPI requires asyncio test support:

```python
import asyncio
import pytest

@pytest.mark.unit
def test_async_order_fetching():
    """Test async order service with mocked async client."""
    from unittest.mock import AsyncMock, MagicMock
    from services.async_order_service import AsyncOrderService

    mock_async_client = AsyncMock()
    mock_async_client.get_orders.return_value = {
        "success": True,
        "data": [{"id": 1, "order_status": "Pending"}]
    }

    mock_order_service = MagicMock()
    mock_event_bus = MagicMock()

    service = AsyncOrderService(
        mock_async_client,
        mock_order_service,
        mock_event_bus
    )

    # Run async method in sync test
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(service.fetch_orders_async())
        assert result is not None
    finally:
        loop.close()
```

### Testing PDF Generation (ApexAPI)

PDF tests can verify structure without pixel-perfect comparison:

```python
import tempfile
from pathlib import Path

def test_packing_list_pdf_generation():
    """Test that packing list PDF is generated with correct structure."""
    from services.print_service import PrintService
    from models import PreRollSummary, PreRollItem

    service = PrintService(license_number="TEST-LICENSE")

    items = [
        PreRollItem(
            name="Test Product 0.5g 6-Pack",
            ordered=50,
            store_name="Test Store",
            order_id=1,
            order_date="2026-01-15",
            packed=25
        )
    ]
    summary = PreRollSummary(items=items)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        output_path = f.name

    try:
        service.generate_packing_list_pdf(summary, output_path)
        # Verify file was created and has content
        assert Path(output_path).exists()
        assert Path(output_path).stat().st_size > 0
    finally:
        Path(output_path).unlink(missing_ok=True)
```

### Testing the EventBus Singleton

The EventBus singleton pattern can cause test interference. Best practices:

```python
import pytest
from events.event_bus import EventBus

@pytest.fixture(autouse=True)
def clean_event_bus():
    """Ensure clean EventBus state for each test."""
    bus = EventBus()
    yield bus
    bus.clear_all_subscriptions()
    bus.clear_history()

def test_subscribe_and_publish(clean_event_bus):
    from events import EventType

    received = []
    clean_event_bus.subscribe(EventType.ORDERS_LOADED, lambda e: received.append(e))
    clean_event_bus.publish(EventType.ORDERS_LOADED, {"count": 3})

    assert len(received) == 1

def test_one_shot_subscription(clean_event_bus):
    from events import EventType

    received = []
    clean_event_bus.subscribe(
        EventType.CACHE_CLEARED,
        lambda e: received.append(e),
        once=True
    )

    clean_event_bus.publish(EventType.CACHE_CLEARED)
    clean_event_bus.publish(EventType.CACHE_CLEARED)

    assert len(received) == 1  # Only fired once
```

### Testing Repository Migrations (ApexAPI)

```python
def test_order_repository_migration(tmp_path):
    """Test that order repository migrations apply cleanly."""
    from repositories.order_repository import OrderRepository

    db_path = str(tmp_path / "test_migrations.db")
    repo = OrderRepository(db_path=db_path)

    # Verify all tables were created
    assert repo.table_exists("orders")
    assert repo.table_exists("print_status")
    assert repo.table_exists("order_cache_metadata")
    assert repo.table_exists("order_status_history")
    assert repo.table_exists("migrations")

    # Verify schema
    schema = repo.get_table_schema("orders")
    column_names = [col["name"] for col in schema]
    assert "id" in column_names
    assert "invoice_number" in column_names
    assert "order_status" in column_names
```

## Test Data Management

### PreRollTracker Test Data

Tests create their own data using the `MODEL` global from `tracker_core.py`:

```python
def test_with_multiple_batches(app):
    from tracker_core import MODEL

    # Create test batches
    batch1_id = MODEL.add_batch(
        strain="Blue Dream",
        input_grams=500,
        target_grams_each=0.5
    )
    batch2_id = MODEL.add_batch(
        strain="OG Kush",
        input_grams=300,
        target_grams_each=1.0
    )

    # Advance stage
    batch1 = MODEL.get_batch(batch1_id)
    batch1.stage = 2  # In progress
    batch1.counts_0_5 = 100
    MODEL.update_batch(batch1)

    # Now test whatever needs multiple batches
    active = MODEL.get_active_batches()
    assert len(active) == 2
```

### ApexAPI Test Data

The conftest fixtures provide reusable sample data. For more complex scenarios, create factory functions:

```python
def make_order(**overrides):
    """Factory for creating test Order instances."""
    from models import Order
    defaults = {
        "id": 1,
        "uuid": "test-uuid",
        "invoice_number": "INV-001",
        "total": "100.00",
        "order_date": "2026-01-15",
        "order_status": "Pending",
        "buyer_company": "Test Buyer",
        "seller_company": "MoM",
        "ship_name": "Test Store",
        "ship_city": "Portland",
        "ship_state": "OR",
        "payment_status": "Paid",
        "items_count": 3,
    }
    defaults.update(overrides)
    return Order(**defaults)

def test_with_custom_orders():
    order_a = make_order(id=1, order_status="Pending")
    order_b = make_order(id=2, order_status="Completed")
    # ... test logic ...
```

## Performance Testing Notes

Neither project currently has formal performance test suites, but critical performance areas to monitor include:

### PreRollTracker Performance-Sensitive Areas

- `/api/data` response time with many active batches (should be under 100ms)
- `/api/finished-goods/` with many METRC packages
- `/api/overview` aggregation queries
- Concurrent API requests during production shifts

### ApexAPI Performance-Sensitive Areas

- Cache warming cycle duration (should complete in under 30 seconds)
- Order list refresh with hundreds of orders
- Product name parsing for large packing lists
- GUI responsiveness during background API calls

Informal benchmarks can be run using pytest-benchmark:

```python
import pytest

def test_batch_serialization_performance(app, benchmark):
    from tracker_core import MODEL
    from database import _preroll_to_row

    batch_id = MODEL.add_batch(strain="Perf Test", input_grams=1000, target_grams_each=0.5)
    batch = MODEL.get_batch(batch_id)

    result = benchmark(_preroll_to_row, batch)
    assert result is not None
```
