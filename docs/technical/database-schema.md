# Database Schema Reference

## Overview

Both PreRollTracker and ApexAPI use SQLite as their database engine. PreRollTracker stores data in `preroll_tracker.db` with 9 tables, while ApexAPI stores data in `apex_data.db` with 13+ tables across multiple repositories.

Both databases enable:

- **Foreign key constraints** (`PRAGMA foreign_keys = ON`)
- **WAL journal mode** (PreRollTracker explicitly; ApexAPI uses default)
- **Row factory** for dict-like access to query results

## PreRollTracker Database Schema

Database file: `preroll_tracker.db`
Connection management: Thread-local via `database.py::get_connection()`
Lock timeout: 30 seconds

### Table: batches

The core production tracking table. Each row represents one cannabis pre-roll production batch with 70+ columns covering every aspect of production from initial material input through centrifuge processing, testing, packaging, and METRC compliance.

| Column | Type | Default | Constraints | Description |
|--------|------|---------|-------------|-------------|
| id | TEXT | -- | PRIMARY KEY | UUID batch identifier |
| strain | TEXT | -- | NOT NULL | Cannabis strain name |
| input_grams | REAL | -- | NOT NULL, CHECK >= 0 | Total grams of input material |
| target_grams_each | REAL | -- | NOT NULL, CHECK >= 0 | Target weight per pre-roll |
| produced | INTEGER | 0 | CHECK >= 0 | Total pre-rolls produced (legacy) |
| grams_used | REAL | 0.0 | CHECK >= 0 | Manual override grams used |
| grams_ground | REAL | 0.0 | CHECK >= 0 | Grams ground from input |
| stage | INTEGER | 0 | CHECK 0-7 | Production stage (0=Not ground through 7=Done) |
| counts_0_5 | INTEGER | 0 | CHECK >= 0 | Actual 0.5g pre-rolls made |
| counts_0_7 | INTEGER | 0 | CHECK >= 0 | Actual 0.7g pre-rolls made |
| counts_1_0 | INTEGER | 0 | CHECK >= 0 | Actual 1.0g pre-rolls made |
| _last_inventory_consumed_0_5 | INTEGER | 0 | -- | Paper inventory tracking for 0.5g |
| _last_inventory_consumed_0_7 | INTEGER | 0 | -- | Paper inventory tracking for 0.7g |
| _last_inventory_consumed_1_0 | INTEGER | 0 | -- | Paper inventory tracking for 1.0g |
| planned_0_5 | INTEGER | 0 | CHECK >= 0 | Planned 0.5g pre-rolls |
| planned_0_7 | INTEGER | 0 | CHECK >= 0 | Planned 0.7g pre-rolls |
| planned_1_0 | INTEGER | 0 | CHECK >= 0 | Planned 1.0g pre-rolls |
| plan_use_grams | REAL | 0.0 | CHECK >= 0 | Material limit for planning (0 = use all) |
| labels_printed | INTEGER | 0 | CHECK >= 0 | Labels printed count |
| display_order | INTEGER | 0 | -- | Custom sort order on dashboard |
| production_start_time | TEXT | NULL | -- | ISO timestamp when stage moved to "In progress" |
| production_end_time | TEXT | NULL | -- | ISO timestamp when stage moved to "Finished" |
| production_duration_hours | REAL | NULL | -- | Calculated production duration |
| archived | INTEGER | 0 | -- | Boolean: 1 = archived, 0 = active |
| harvest_date | TEXT | NULL | -- | ISO date of harvest (YYYY-MM-DD) |
| bay_number | TEXT | NULL | -- | Bay/location identifier |
| thc_percent | REAL | NULL | -- | THC percentage (0-100) |
| thca_percent | REAL | NULL | -- | THCa percentage (0-100) |
| tac_percent | REAL | NULL | -- | Total Active Cannabinoids % |
| cbd_percent | REAL | NULL | -- | CBD percentage (0-100) |
| origin_metrc_number | TEXT | NULL | -- | Original METRC tracking number |
| new_metrc_created | INTEGER | 0 | -- | Boolean: new METRC package created |
| centrifuge_rpm | INTEGER | NULL | -- | Centrifuge RPM setting (universal mode) |
| centrifuge_time_seconds | INTEGER | NULL | -- | Centrifuge time in seconds |
| centrifuge_cycles | INTEGER | NULL | -- | Number of centrifuge cycles (1-3) |
| centrifuge_fill_gauge_cycle1 | REAL | NULL | -- | Fill gauge reading cycle 1 (1-12) |
| centrifuge_fill_gauge_cycle2 | REAL | NULL | -- | Fill gauge reading cycle 2 |
| centrifuge_machine | TEXT | NULL | -- | Machine: 'silver_bullet' or 'lab_geek' |
| centrifuge_settings_by_size | TEXT | NULL | -- | JSON: per-size centrifuge settings dict |
| new_metrc_number | TEXT | NULL | -- | New METRC number when package created |
| metrc_transferred | INTEGER | 0 | -- | Boolean: inventory transferred in METRC |
| metrc_batch_created | INTEGER | 0 | -- | Boolean: METRC batch package created |
| testing_status | TEXT | 'none' | -- | Testing workflow state (none/sample_created/sample_sent/results_received/test_passed/test_failed) |
| test_package_id | TEXT | NULL | -- | Test package identifier |
| testing_lab | TEXT | NULL | -- | Lab name for testing |
| test_date | TEXT | NULL | -- | ISO date when sample sent |
| test_results | TEXT | NULL | -- | Test results data |
| testing_notes | TEXT | NULL | -- | Free-form testing notes |
| packaging_status | TEXT | 'available' | -- | Packaging state (available/waiting_materials/waiting_containers/blocked_other) |
| packaging_blocker_type | TEXT | NULL | -- | What is blocking packaging |
| packaging_notes | TEXT | NULL | -- | Packaging blocker details |
| packaging_blocked_since | TEXT | NULL | -- | ISO timestamp when blocking started |
| cached_production_rate | REAL | NULL | -- | Cached rate (pre-rolls/hour) |
| rate_calculation_time | TEXT | NULL | -- | When rate was last calculated |
| rate_history | TEXT | NULL | -- | JSON array of rate snapshots |
| rate_metrics | TEXT | NULL | -- | JSON dict of computed rate statistics |
| last_rate_update | TEXT | NULL | -- | ISO timestamp of last rate snapshot |
| production_sessions | TEXT | NULL | -- | JSON array of work sessions with start/end times |
| current_session_start | TEXT | NULL | -- | Current session start time |
| total_work_hours | REAL | 0.0 | -- | Cumulative work hours across sessions |
| paper_size_override | TEXT | NULL | -- | Override paper size: '0_5', '0_7', '1_0' |
| is_infused | INTEGER | 0 | -- | Boolean: infused product with multiple sources |
| source_materials | TEXT | NULL | -- | JSON array of source material dicts |
| weight_log_0_5 | TEXT | NULL | -- | JSON array of weight measurements for 0.5g |
| weight_log_0_7 | TEXT | NULL | -- | JSON array of weight measurements for 0.7g |
| weight_log_1_0 | TEXT | NULL | -- | JSON array of weight measurements for 1.0g |
| running_yield_0_5 | REAL | 0.0 | -- | Running yield percentage for 0.5g |
| running_yield_0_7 | REAL | 0.0 | -- | Running yield percentage for 0.7g |
| running_yield_1_0 | REAL | 0.0 | -- | Running yield percentage for 1.0g |
| last_weight_check_count_0_5 | INTEGER | 0 | -- | Last count when weight checked for 0.5g |
| last_weight_check_count_0_7 | INTEGER | 0 | -- | Last count when weight checked for 0.7g |
| last_weight_check_count_1_0 | INTEGER | 0 | -- | Last count when weight checked for 1.0g |
| last_weight_check_date_0_5 | TEXT | NULL | -- | ISO date of last weight check for 0.5g |
| last_weight_check_date_0_7 | TEXT | NULL | -- | ISO date of last weight check for 0.7g |
| last_weight_check_date_1_0 | TEXT | NULL | -- | ISO date of last weight check for 1.0g |
| final_weight_0_5 | REAL | 0.0 | -- | Final weight for 0.5g batch completion |
| final_weight_0_7 | REAL | 0.0 | -- | Final weight for 0.7g batch completion |
| final_weight_1_0 | REAL | 0.0 | -- | Final weight for 1.0g batch completion |
| grind_size | TEXT | NULL | -- | Grind setting: 'fine', 'medium', 'coarse' |
| packaged_singles | INTEGER | 0 | -- | Individual tubes packaged |
| packaged_6_packs | INTEGER | 0 | -- | 6-packs made |
| packaged_12_packs | INTEGER | 0 | -- | 12-packs made |
| loose_tupperware | INTEGER | 0 | -- | Loose pre-rolls for flexible packing |

**Indexes on batches:**

| Index | Column(s) | Purpose |
|-------|-----------|---------|
| idx_batches_strain | strain | Filter by strain name |
| idx_batches_stage | stage | Filter by production stage |
| idx_batches_archived | archived | Separate active/archived batches |
| idx_batches_metrc_number | new_metrc_number | METRC number lookup |

### Table: audit_log

Tracks every field change made to any batch. Used for accountability and debugging.

| Column | Type | Default | Constraints | Description |
|--------|------|---------|-------------|-------------|
| id | INTEGER | -- | PRIMARY KEY AUTOINCREMENT | Auto-incrementing audit ID |
| batch | TEXT | -- | NOT NULL | Batch ID that was modified |
| strain | TEXT | -- | NOT NULL | Strain name (denormalized for readability) |
| ts | TEXT | -- | NOT NULL | ISO timestamp of the change |
| field | TEXT | -- | NOT NULL | Name of the field that changed |
| old | TEXT | NULL | -- | Previous value (as string) |
| new | TEXT | NULL | -- | New value (as string) |

**Indexes:**

| Index | Column(s) | Purpose |
|-------|-----------|---------|
| idx_audit_batch | batch | Look up changes for a specific batch |
| idx_audit_timestamp | ts | Chronological queries |

### Table: finished_goods

Tracks METRC packages in finished goods inventory. Each package has a unique METRC number and tracks grams available, ordered, packed, and fulfilled.

| Column | Type | Default | Constraints | Description |
|--------|------|---------|-------------|-------------|
| metrc_number | TEXT | -- | PRIMARY KEY | METRC tracking number |
| strain | TEXT | -- | NOT NULL | Cannabis strain |
| initial_grams | REAL | -- | NOT NULL | Starting weight in grams |
| current_grams | REAL | -- | NOT NULL | Current available grams |
| status | TEXT | 'active' | -- | active/depleted/retired |
| created_date | TEXT | NULL | -- | When package was created |
| updated_date | TEXT | NULL | -- | Last modification time |
| notes | TEXT | NULL | -- | Free-form notes |
| source_batch_id | TEXT | NULL | FK -> batches(id) | Which batch produced this package |
| grams_ordered | REAL | 0.0 | -- | Grams in pending orders |
| grams_packed | REAL | 0.0 | -- | Grams packed for current orders |
| grams_packed_lifetime | REAL | 0.0 | -- | Total grams packed historically |
| grams_fulfilled | REAL | 0.0 | -- | Grams shipped/delivered |
| sku_breakdown | TEXT | NULL | -- | JSON: grams by SKU size |
| apex_auto_inventory | INTEGER | 0 | -- | Boolean: auto-sync with Apex |
| apex_units | TEXT | NULL | -- | JSON: Apex inventory unit mapping |
| apex_sku_settings | TEXT | NULL | -- | JSON: Apex SKU configuration |
| processed_decrements | TEXT | NULL | -- | JSON: tracked Apex decrements |
| custom_skus | TEXT | NULL | -- | JSON: custom SKU definitions |
| physical_grams_override | REAL | NULL | -- | Manual weight override |

**Indexes:**

| Index | Column(s) | Purpose |
|-------|-----------|---------|
| idx_finished_goods_status | status | Filter active/depleted packages |
| idx_finished_goods_strain | strain | Filter by strain |
| idx_finished_goods_source | source_batch_id | Find packages from a batch |

### Table: finished_goods_history

Historical snapshots of finished goods changes for auditing and trending.

| Column | Type | Default | Constraints | Description |
|--------|------|---------|-------------|-------------|
| id | INTEGER | -- | PRIMARY KEY AUTOINCREMENT | Auto-incrementing ID |
| metrc_number | TEXT | -- | NOT NULL | METRC tracking number |
| timestamp | TEXT | -- | NOT NULL | ISO timestamp of change |
| change_type | TEXT | -- | NOT NULL | Type of change (created/deducted/added/etc.) |
| current_grams | REAL | -- | NOT NULL | Grams after this change |
| grams_ordered | REAL | 0.0 | -- | Ordered grams at this point |
| grams_packed | REAL | 0.0 | -- | Packed grams at this point |
| grams_fulfilled | REAL | 0.0 | -- | Fulfilled grams at this point |
| status | TEXT | NULL | -- | Status at time of change |
| details | TEXT | NULL | -- | JSON details about the change |

**Indexes:**

| Index | Column(s) | Purpose |
|-------|-----------|---------|
| idx_history_metrc | metrc_number | History for one METRC package |
| idx_history_timestamp | timestamp | Chronological queries |

### Table: inventory

Tracks paper/cone inventory by pre-roll size.

| Column | Type | Default | Constraints | Description |
|--------|------|---------|-------------|-------------|
| size | TEXT | -- | PRIMARY KEY | Size key: '0_5', '0_7', '1_0' |
| boxes | INTEGER | 0 | -- | Number of full boxes |
| individual_papers | INTEGER | 0 | -- | Loose papers count |
| low_threshold | INTEGER | 5 | -- | Alert threshold (boxes) |
| last_updated | TEXT | NULL | -- | ISO timestamp |

### Table: inventory_usage

Daily paper consumption log for tracking usage patterns.

| Column | Type | Default | Constraints | Description |
|--------|------|---------|-------------|-------------|
| id | INTEGER | -- | PRIMARY KEY AUTOINCREMENT | Auto-incrementing ID |
| size | TEXT | -- | NOT NULL | Paper size consumed |
| timestamp | TEXT | -- | NOT NULL | When consumption occurred |
| papers_used | INTEGER | -- | NOT NULL | Number of papers consumed |
| batch_id | TEXT | NULL | -- | Which batch consumed them |

**Indexes:**

| Index | Column(s) | Purpose |
|-------|-----------|---------|
| idx_usage_size | size | Usage by size |
| idx_usage_timestamp | timestamp | Chronological queries |
| idx_usage_batch | batch_id | Usage per batch |

### Table: settings

Key-value store replacing the legacy `settings.json` file.

| Column | Type | Default | Constraints | Description |
|--------|------|---------|-------------|-------------|
| key | TEXT | -- | PRIMARY KEY | Setting name |
| value | TEXT | -- | NOT NULL | Setting value (JSON-encoded) |
| updated_at | TEXT | -- | NOT NULL | Last modification timestamp |

### Table: wholesale_holds

Inventory reservations for the wholesale team, preventing over-allocation of finished goods.

| Column | Type | Default | Constraints | Description |
|--------|------|---------|-------------|-------------|
| id | TEXT | -- | PRIMARY KEY | UUID hold identifier |
| metrc_number | TEXT | -- | NOT NULL, FK -> finished_goods ON DELETE CASCADE | METRC package being held |
| sku_name | TEXT | -- | NOT NULL | SKU being reserved |
| quantity | INTEGER | -- | NOT NULL | Units reserved |
| created_date | TEXT | -- | NOT NULL | When the hold was created |
| notes | TEXT | NULL | -- | Hold notes |

**Indexes:**

| Index | Column(s) | Purpose |
|-------|-----------|---------|
| idx_wholesale_holds_metrc | metrc_number | Holds for a METRC package |
| idx_wholesale_holds_sku | sku_name | Holds by SKU |

### Table: schema_version

Tracks applied database migrations.

| Column | Type | Default | Constraints | Description |
|--------|------|---------|-------------|-------------|
| version | INTEGER | -- | PRIMARY KEY | Migration version number |
| migration_name | TEXT | -- | NOT NULL | Human-readable migration name |
| applied_at | TEXT | -- | NOT NULL | When the migration was applied |
| checksum | TEXT | NULL | -- | Optional integrity checksum |

## ApexAPI Database Schema

Database file: `apex_data.db`
Connection management: Per-operation context manager via `BaseRepository.get_connection()`

### Table: orders

Cached order data from the Apex Trading API.

| Column | Type | Default | Constraints | Description |
|--------|------|---------|-------------|-------------|
| id | INTEGER | -- | PRIMARY KEY | Apex Trading order ID |
| uuid | TEXT | '' | NOT NULL | Apex Trading UUID |
| invoice_number | TEXT | '' | NOT NULL | Invoice number (e.g., MoM-2026001) |
| total | TEXT | '' | NOT NULL | Order total as string |
| order_date | TEXT | '' | NOT NULL | Date order was placed |
| order_status | TEXT | '' | NOT NULL | Current status (Pending/Completed/Cancelled) |
| buyer_company | TEXT | '' | NOT NULL | Buyer company name |
| seller_company | TEXT | '' | NOT NULL | Seller company name |
| ship_name | TEXT | '' | NOT NULL | Ship-to name |
| ship_city | TEXT | '' | NOT NULL | Ship-to city |
| ship_state | TEXT | '' | NOT NULL | Ship-to state |
| payment_status | TEXT | '' | NOT NULL | Payment status |
| items_count | INTEGER | 0 | NOT NULL | Number of line items |
| printed | BOOLEAN | FALSE | NOT NULL | Whether order has been printed |
| print_timestamp | TEXT | NULL | -- | When order was printed |
| is_third_party | BOOLEAN | FALSE | -- | Whether this is a third-party order |
| cached_at | DATETIME | CURRENT_TIMESTAMP | -- | When order was cached |
| last_updated | DATETIME | CURRENT_TIMESTAMP | -- | Last update time |

**Indexes:**

| Index | Column(s) | Purpose |
|-------|-----------|---------|
| idx_orders_order_status | order_status | Filter by status |
| idx_orders_order_date | order_date | Chronological queries |
| idx_orders_buyer | buyer_company | Filter by buyer |
| idx_orders_printed | printed | Find unprinted orders |

### Table: print_status

Tracks which orders have been printed and when.

| Column | Type | Default | Constraints | Description |
|--------|------|---------|-------------|-------------|
| order_id | INTEGER | -- | PRIMARY KEY, FK -> orders(id) | Order that was printed |
| printed_at | DATETIME | -- | NOT NULL | Print timestamp |
| status | TEXT | 'printed' | -- | Print status |
| printer_name | TEXT | NULL | -- | Which printer was used |
| print_method | TEXT | NULL | -- | How it was printed (direct/PDF/etc.) |

### Table: order_cache_metadata

Metadata about cached order details for efficient cache invalidation.

| Column | Type | Default | Constraints | Description |
|--------|------|---------|-------------|-------------|
| order_id | INTEGER | -- | PRIMARY KEY, FK -> orders(id) | Cached order |
| third_party_checked_at | DATETIME | NULL | -- | When third-party status was checked |
| third_party_status | BOOLEAN | NULL | -- | Whether order is third-party |
| item_count | INTEGER | 0 | -- | Cached item count |
| cache_expiry | DATETIME | NULL | -- | When this cache entry expires |
| error_message | TEXT | NULL | -- | Error from last check |

### Table: order_status_history

Tracks order status changes over time.

| Column | Type | Default | Constraints | Description |
|--------|------|---------|-------------|-------------|
| id | INTEGER | -- | PRIMARY KEY AUTOINCREMENT | Auto-incrementing ID |
| order_id | INTEGER | -- | NOT NULL, FK -> orders(id) | Order that changed |
| old_status | TEXT | NULL | -- | Previous status |
| new_status | TEXT | -- | NOT NULL | New status |
| changed_at | DATETIME | CURRENT_TIMESTAMP | -- | When status changed |
| changed_by | TEXT | 'system' | -- | Who/what changed it |

### Table: config

Application configuration key-value store with metadata.

| Column | Type | Default | Constraints | Description |
|--------|------|---------|-------------|-------------|
| key | TEXT | -- | PRIMARY KEY | Configuration key |
| value | TEXT | -- | NOT NULL | Configuration value |
| data_type | TEXT | -- | NOT NULL | Value type (string/int/bool/json) |
| category | TEXT | NULL | -- | Configuration category |
| description | TEXT | NULL | -- | Human-readable description |
| created_at | DATETIME | CURRENT_TIMESTAMP | -- | Creation time |
| updated_at | DATETIME | CURRENT_TIMESTAMP | -- | Last update time |

**Indexes:**

| Index | Column(s) | Purpose |
|-------|-----------|---------|
| idx_config_category | category | Filter by category |

### Table: user_preferences

Per-user UI preferences and settings.

| Column | Type | Default | Constraints | Description |
|--------|------|---------|-------------|-------------|
| id | INTEGER | -- | PRIMARY KEY AUTOINCREMENT | Auto-incrementing ID |
| user_id | TEXT | 'default' | -- | User identifier |
| preference_key | TEXT | -- | NOT NULL | Preference name |
| preference_value | TEXT | -- | NOT NULL | Preference value |
| data_type | TEXT | -- | NOT NULL | Value type |
| created_at | DATETIME | CURRENT_TIMESTAMP | -- | Creation time |
| updated_at | DATETIME | CURRENT_TIMESTAMP | -- | Last update time |

**Constraints:** UNIQUE(user_id, preference_key)

### Table: config_history

Audit trail for configuration changes.

| Column | Type | Default | Constraints | Description |
|--------|------|---------|-------------|-------------|
| id | INTEGER | -- | PRIMARY KEY AUTOINCREMENT | Auto-incrementing ID |
| config_key | TEXT | -- | NOT NULL | Which config was changed |
| old_value | TEXT | NULL | -- | Previous value |
| new_value | TEXT | NULL | -- | New value |
| changed_by | TEXT | 'system' | -- | Who made the change |
| changed_at | DATETIME | CURRENT_TIMESTAMP | -- | When |
| change_reason | TEXT | NULL | -- | Why it was changed |

**Indexes:**

| Index | Column(s) | Purpose |
|-------|-----------|---------|
| idx_config_history_key | config_key | History for one key |
| idx_config_history_changed_at | changed_at | Chronological queries |

### Table: system_settings

System-level settings with sensitivity marking.

| Column | Type | Default | Constraints | Description |
|--------|------|---------|-------------|-------------|
| setting_name | TEXT | -- | PRIMARY KEY | Setting name |
| setting_value | TEXT | -- | NOT NULL | Setting value |
| is_sensitive | BOOLEAN | FALSE | -- | Whether value should be masked in logs |
| last_modified | DATETIME | CURRENT_TIMESTAMP | -- | Last update |
| modified_by | TEXT | 'system' | -- | Who modified |

### Table: preroll_items

Active pre-roll packing list items with per-store order and packing tracking.

| Column | Type | Default | Constraints | Description |
|--------|------|---------|-------------|-------------|
| id | INTEGER | -- | PRIMARY KEY AUTOINCREMENT | Auto-incrementing ID |
| order_id | INTEGER | -- | NOT NULL | Apex Trading order ID |
| product_name | TEXT | -- | NOT NULL | Full product name |
| store_name | TEXT | -- | NOT NULL | Store that ordered |
| ordered | INTEGER | -- | NOT NULL | Units ordered |
| packed | INTEGER | 0 | -- | Units packed |
| initials | TEXT | '' | -- | Packer initials |
| notes | TEXT | '' | -- | Item notes |
| order_date | TEXT | -- | NOT NULL | Order date |
| is_new | BOOLEAN | FALSE | -- | Whether order is < 24 hours old |
| last_updated | DATETIME | CURRENT_TIMESTAMP | -- | Last update |

**Constraints:** UNIQUE(order_id, product_name)

**Indexes:**

| Index | Column(s) | Purpose |
|-------|-----------|---------|
| idx_preroll_order_id | order_id | Items for an order |
| idx_preroll_store | store_name | Items by store |
| idx_preroll_product | product_name | Items by product |
| idx_preroll_updated | last_updated | Recently modified items |

### Table: preroll_metadata

Single-row metadata table for packing list state.

| Column | Type | Default | Constraints | Description |
|--------|------|---------|-------------|-------------|
| id | INTEGER | -- | PRIMARY KEY, CHECK (id = 1) | Always 1 (single row) |
| last_refresh_time | DATETIME | -- | NOT NULL | When data was last refreshed from API |
| filter_type | TEXT | 'active' | -- | Current filter mode |
| date_range_start | TEXT | NULL | -- | Date range filter start |
| date_range_end | TEXT | NULL | -- | Date range filter end |
| total_items | INTEGER | 0 | -- | Total items in current view |

### Table: preroll_items_archive

Historical completed orders archived from the active packing list.

| Column | Type | Default | Constraints | Description |
|--------|------|---------|-------------|-------------|
| id | INTEGER | -- | PRIMARY KEY AUTOINCREMENT | Auto-incrementing ID |
| order_id | INTEGER | -- | NOT NULL | Original order ID |
| product_name | TEXT | -- | NOT NULL | Product name |
| store_name | TEXT | -- | NOT NULL | Store name |
| ordered | INTEGER | -- | NOT NULL | Units ordered |
| packed | INTEGER | 0 | -- | Units packed |
| initials | TEXT | '' | -- | Packer initials |
| notes | TEXT | '' | -- | Notes |
| order_date | TEXT | -- | NOT NULL | Original order date |
| invoice_number | TEXT | '' | -- | Invoice number |
| batch_name | TEXT | '' | -- | METRC batch name |
| compact_display_name | TEXT | '' | -- | Parsed compact display name |
| archived_at | DATETIME | CURRENT_TIMESTAMP | -- | When archived |
| completion_date | TEXT | '' | -- | When order was completed |

### Table: edibles_orders

Historical edibles order data for sell-through analysis.

| Column | Type | Default | Constraints | Description |
|--------|------|---------|-------------|-------------|
| id | INTEGER | -- | PRIMARY KEY AUTOINCREMENT | Auto-incrementing ID |
| order_id | INTEGER | -- | NOT NULL | Apex Trading order ID |
| order_date | DATE | -- | NOT NULL | Order date |
| buyer_company | TEXT | -- | NOT NULL | Buyer company |
| product_name | TEXT | -- | NOT NULL | Product name |
| product_category | TEXT | -- | NOT NULL | Product category |
| product_type | TEXT | -- | NOT NULL | Product type |
| quantity | INTEGER | -- | NOT NULL | Units ordered |
| unit_price | REAL | NULL | -- | Price per unit |
| total_price | REAL | NULL | -- | Line item total |
| is_wholesale | BOOLEAN | 1 | NOT NULL | Whether this is a wholesale order |
| created_at | DATETIME | CURRENT_TIMESTAMP | -- | Record creation time |
| updated_at | DATETIME | CURRENT_TIMESTAMP | -- | Last update |

### Table: migrations

Tracks applied database migrations for all repositories.

| Column | Type | Default | Constraints | Description |
|--------|------|---------|-------------|-------------|
| id | INTEGER | -- | PRIMARY KEY AUTOINCREMENT | Auto-incrementing ID |
| migration_name | TEXT | -- | UNIQUE, NOT NULL | Migration identifier |
| applied_at | DATETIME | CURRENT_TIMESTAMP | -- | When applied |

## Entity Relationships

### PreRollTracker Relationships

```
batches (id)
    |
    +---< finished_goods (source_batch_id)
    |         |
    |         +---< finished_goods_history (metrc_number)
    |         |
    |         +---< wholesale_holds (metrc_number) [ON DELETE CASCADE]
    |
    +---< audit_log (batch)
    |
    +---< inventory_usage (batch_id)

inventory (size)
    |
    +---< inventory_usage (size)

settings (key) -- standalone

schema_version (version) -- standalone
```

Key relationships:

- `finished_goods.source_batch_id` references `batches.id` -- tracks which batch produced a METRC package
- `wholesale_holds.metrc_number` references `finished_goods.metrc_number` with CASCADE delete -- removing a finished good removes all its holds
- `audit_log.batch` and `inventory_usage.batch_id` reference batches by ID but without foreign key constraints (for flexibility with archived/deleted batches)

### ApexAPI Relationships

```
orders (id)
    |
    +---< print_status (order_id)
    |
    +---< order_cache_metadata (order_id)
    |
    +---< order_status_history (order_id)

preroll_items (id)
    |
    +--- (references orders.id via order_id, no FK constraint)

preroll_metadata (id=1) -- singleton

preroll_items_archive (id) -- standalone archive

config (key) -- standalone
user_preferences (id) -- standalone
config_history (id) -- standalone
system_settings (setting_name) -- standalone
edibles_orders (id) -- standalone
migrations (id) -- standalone
```

## Migration History and Strategy

### PreRollTracker Migrations

Migrations are stored in `migrations/versions/` and applied automatically by `database.py::init_db()`.

| Version | File | Description |
|---------|------|-------------|
| 001 | 001_baseline.py | No-op baseline (schema already created by init_db) |
| 002 | 002_add_check_constraints.py | Adds CHECK constraints via table recreation (SQLite limitation) |
| 003 | 003_add_plan_use_grams.py | Adds plan_use_grams column (idempotent -- skips if migration 002 already added it) |

Migration strategy:

- Each migration has `up(conn)` and `down(conn)` methods
- `down()` is typically `raise RuntimeError` since SQLite cannot easily reverse schema changes
- Migrations are tracked in the `schema_version` table with version number, name, timestamp, and optional checksum
- The `_add_column_if_missing()` helper makes column additions idempotent
- For constraint changes (migration 002), the table is recreated: create new table -> copy data -> drop old -> rename new

### ApexAPI Migrations

ApexAPI uses repository-level migrations defined in each repository's `get_migrations()` method:

- Migrations are tracked in a shared `migrations` table with unique migration names
- Each repository can define its own migrations as a dict of `{migration_name: sql_string}`
- Migrations are applied during `BaseRepository._init_database()` -- called on first connection
- Failed migrations trigger a rollback and re-raise the exception

## Cross-App Data Relationships

### METRC Number as Universal Key

Both applications use METRC tracking numbers as the canonical identifier for cannabis packages:

- **PreRollTracker** stores METRC numbers in `batches.new_metrc_number` and `finished_goods.metrc_number`
- **ApexAPI** maps Apex Trading product names to METRC numbers via `BatchMappingService` and `batch_mapping_cache.json`
- The packing list system in ApexAPI shows METRC numbers from `PreRollItem.batch_name`

### Sync State Fields

The `finished_goods` table in PreRollTracker has several fields dedicated to ApexAPI synchronization:

- `apex_auto_inventory` -- Whether this package auto-syncs with Apex Trading inventory
- `apex_units` -- JSON mapping of unit types for Apex
- `apex_sku_settings` -- JSON configuration for how SKUs map between systems
- `processed_decrements` -- JSON tracking which inventory decrements have been applied
- `grams_ordered` / `grams_packed` / `grams_fulfilled` -- Updated by both systems during the order lifecycle

### Data Flow During Order Fulfillment

1. Order created in Apex Trading API
2. ApexAPI fetches order, caches in `orders` table
3. ApexAPI creates `preroll_items` entries with product name parsing
4. User packs items in ApexAPI, updating `preroll_items.packed`
5. ApexAPI syncs packed quantities to PreRollTracker via Dashboard API
6. PreRollTracker updates `finished_goods.grams_packed`
7. Completion triggers `finished_goods.grams_fulfilled` update and history entry
