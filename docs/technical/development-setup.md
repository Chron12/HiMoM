# Development Setup Guide

## Prerequisites

Before setting up either project, ensure you have the following installed:

| Requirement | Minimum Version | Purpose |
|------------|----------------|---------|
| Python | 3.7+ (3.10+ recommended) | Runtime for both applications |
| pip | Latest | Package management |
| Git | 2.x | Version control |
| SQLite3 | 3.24+ | Database engine (usually bundled with Python) |
| OpenSSL | 1.1+ | Backup encryption (PreRollTracker) |
| GitHub CLI (gh) | 2.x | Backup uploads (PreRollTracker, optional) |

### Platform-Specific Requirements

**macOS:**

- Xcode Command Line Tools (`xcode-select --install`) for bcrypt compilation
- keyring works natively with macOS Keychain

**Linux:**

- `python3-dev` and `build-essential` for bcrypt compilation
- `libffi-dev` for cryptography package
- `keyrings.alt` package for keyring support (or configure GNOME Keyring / KWallet)

**Windows:**

- Visual C++ Build Tools for bcrypt compilation
- `pywin32` package for printing support in ApexAPI
- keyring works natively with Windows Credential Manager

## PreRollTracker Setup

### Step 1: Clone the Repository

```bash
git clone <repository-url> ~/PycharmProjects/PreRollTracker
cd ~/PycharmProjects/PreRollTracker
```

### Step 2: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:

- Flask 3.0.3 and extensions (Flask-WTF, Flask-Limiter, Flask-Compress, Flask-Talisman)
- Gunicorn 21.2.0 (production WSGI server)
- bcrypt 4.0.1 (password hashing)
- python-dotenv 1.0.0 (environment variable loading)
- NumPy (production rate regression analysis)
- sentry-sdk with Flask integration (error monitoring)
- pytest and pytest-flask (testing)

### Step 4: Configure Environment Variables

Create a `.env` file in the project root:

```bash
# REQUIRED: Secret key for Flask sessions and CSRF protection
# Generate with: python -c 'import secrets; print(secrets.token_hex(32))'
SECRET_KEY=your-secret-key-here

# REQUIRED: Admin password hash (bcrypt)
# Generate with: python setup_admin_password.py
ADMIN_PASSWORD_HASH=$2b$12$...your-hash-here

# OPTIONAL: Sentry DSN for error monitoring
SENTRY_DSN=https://your-dsn@sentry.io/project-id

# OPTIONAL: Sentry environment tag
SENTRY_ENV=development

# OPTIONAL: Backup encryption key
# Generate with: python -c 'import secrets; print(secrets.token_hex(32))'
BACKUP_ENCRYPTION_KEY=your-encryption-key-here

# OPTIONAL: GitHub token for backup uploads
GITHUB_TOKEN=ghp_...

# OPTIONAL: Pushover notification keys
PUSHOVER_USER_KEY=your-user-key
PUSHOVER_APP_TOKEN=your-app-token
```

### Step 5: Set Up Admin Password

```bash
python setup_admin_password.py
```

This will prompt you for a password and output a bcrypt hash. Add the hash to your `.env` file as `ADMIN_PASSWORD_HASH`.

Alternatively, generate one programmatically:

```python
from auth_utils import password_manager
hash_value = password_manager.hash_password("your-password")
print(f"ADMIN_PASSWORD_HASH={hash_value}")
```

### Step 6: Initialize the Database

The database initializes automatically when the application starts. However, you can initialize it explicitly:

```python
python -c "from database import init_db; init_db('preroll_tracker.db')"
```

This creates `preroll_tracker.db` with all 9 tables and runs any pending migrations from `migrations/versions/`.

The default database path used at runtime is `data/preroll.db` (set by `database.DEFAULT_DB_PATH`). The root-level `preroll_tracker.db` is used by the legacy code path in `tracker_core.py`.

### Step 7: Run the Development Server

```bash
# Development mode (auto-reload, debug mode)
python app.py

# Or explicitly:
flask run --host=0.0.0.0 --port=5000 --debug
```

The dashboard will be available at `http://localhost:5000`.

### Step 8: Run the Production Server

```bash
gunicorn -w 4 -b 0.0.0.0:5000 run:app
```

This starts 4 worker processes. The `run.py` entry point configures production logging with rotating file handlers.

### Step 9: Verify the Setup

1. Open `http://localhost:5000` -- should see the public dashboard
2. Open `http://localhost:5000/admin/` -- should redirect to login
3. Log in with your admin password
4. Create a test batch through the admin interface
5. Verify it appears on the public dashboard

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_database.py

# Run a specific test
pytest tests/test_database.py::test_init_db

# Run with coverage
pytest --cov=. --cov-report=html
```

The test suite uses:

- A temporary SQLite database for each test (via `tmp_path` fixture)
- Monkeypatched `DEFAULT_DB_PATH` to isolate tests from production data
- CSRF disabled in test mode
- A pre-authenticated client fixture (`authenticated_client`) for admin endpoints

### Project Configuration Reference

| Config | Location | Purpose |
|--------|----------|---------|
| Flask config | `config.py` | Dev/Test/Prod Flask settings |
| Environment | `.env` | Secrets and deployment config |
| Database | `database.py::DEFAULT_DB_PATH` | SQLite file location |
| Migrations | `migrations/versions/` | Schema evolution |
| Backup | `backup_manager.py` constants | Backup directory, intervals, retention |

## ApexAPI Setup

### Step 1: Clone the Repository

```bash
git clone <repository-url> ~/PycharmProjects/ApexAPI
cd ~/PycharmProjects/ApexAPI
```

### Step 2: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:

- requests (sync HTTP client)
- aiohttp, asyncio-throttle (async HTTP client)
- pandas (data processing)
- customtkinter (modern GUI framework)
- reportlab (PDF generation)
- keyring, cryptography (secure credential storage)
- ruff (linting)
- pytest, responses (testing)

### Step 4: Configure the Application

Copy the template configuration:

```bash
cp apex_config_template.json apex_config.json
```

Edit `apex_config.json`:

```json
{
    "license_number": "YOUR-LICENSE-NUMBER",
    "selected_printer": null,
    "auto_refresh_enabled": true,
    "auto_refresh_interval": 5,
    "offer_startup_print": true,
    "cache_warming_enabled": true,
    "cache_warming_interval_minutes": 60,
    "cache_directory": "cache",
    "dashboard_url": "https://himomstats.online",
    "dashboard_api_key": "your-prerolltracker-api-key",
    "batch_inventory_sync": {
        "enabled": false,
        "auto_start": false
    }
}
```

Key configuration values:

| Key | Required | Description |
|-----|----------|-------------|
| `license_number` | Yes | Your cannabis license number for packing lists |
| `dashboard_url` | For sync | URL of your PreRollTracker instance |
| `dashboard_api_key` | For sync | API key from PreRollTracker settings |
| `cache_warming_enabled` | No | Enable/disable background cache warming (default: true) |
| `auto_refresh_interval` | No | Minutes between auto-refresh (default: 5) |

### Step 5: Set Up API Token

The Apex Trading API token can be configured in two ways:

**Option A: Secure Storage (Recommended)**

Launch the GUI, go to Settings, and enter your API token. It will be stored in the OS keyring (macOS Keychain, Windows Credential Manager, or Linux Secret Service).

**Option B: Manual Configuration**

If keyring is unavailable, add the token to `apex_config.json`:

```json
{
    "api_token": "your-apex-trading-api-token"
}
```

Note: The application will automatically migrate tokens from JSON to keyring when keyring becomes available.

### Step 6: Running the GUI

```bash
python apex_gui.py
```

The application will:

1. Create the `ServiceContainer` and initialize all services
2. Read configuration from `apex_config.json` and keyring
3. Start the cache warming background thread
4. Display the main order management window

### Step 7: Verify the Setup

1. The main window should display with a toolbar and empty order list
2. Click the refresh button or wait for auto-refresh
3. If the API token is valid, orders should populate
4. Check the status bar for connection and cache status

### Running Tests

```bash
# Run all tests
pytest

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run a specific test file
pytest tests/unit/test_order_service.py

# Run with verbose output
pytest -v --tb=short

# Run with coverage
pytest --cov=. --cov-report=html
```

The test suite is organized as:

- **Unit tests** (`tests/unit/`) -- Fast tests with no I/O. Services tested with mocked dependencies. HTTP responses mocked via the `responses` library.
- **Integration tests** (`tests/integration/`) -- Tests with real SQLite databases in `tmp_path`. Repository CRUD operations tested end-to-end.

Test configuration is defined in `pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
markers =
    unit: Fast unit tests (no I/O)
    integration: Tests with database/file I/O
```

### Building the Executable

ApexAPI can be packaged as a standalone executable using PyInstaller:

**macOS Build:**

```bash
python build_exe.py
# or directly with PyInstaller:
pyinstaller apex_gui.spec
```

**Windows Build:**

```bash
python build_windows.py
# or directly:
pyinstaller apex_gui_windows.spec
```

The spec files configure:

- Single-file executable (`--onefile` or `--onedir` depending on platform)
- Hidden imports for dynamically loaded modules
- Data files (config templates, cache directories)
- Icon and application metadata

Build output goes to `dist/` directory. The executable includes all Python dependencies and can run without a Python installation.

### Linting

ApexAPI uses Ruff for code quality:

```bash
# Check for issues
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .
```

Ruff configuration is in `ruff.toml`.

## Development Workflow

### PreRollTracker Development Cycle

1. Make changes to Python code (blueprints, tracker_core, database)
2. For database schema changes, create a new migration in `migrations/versions/`
3. For frontend changes, edit the standalone HTML files directly
4. Run the dev server (`python app.py`) which auto-reloads on changes
5. Test API changes with curl or the browser console
6. Run `pytest` before committing
7. Deploy with `deploy.sh` or manually via git pull + `sudo systemctl restart preroll-tracker`

### ApexAPI Development Cycle

1. Make changes to services, repositories, or GUI modules
2. For new services, register them in `ServiceContainer.initialize()`
3. For new event types, add to `EventType` enum
4. Run `ruff check .` to catch issues early
5. Run `pytest -m unit` for quick feedback
6. Run `pytest -m integration` for database tests
7. Test the GUI by running `python apex_gui.py`
8. Build the executable when ready for distribution

### Common Development Tasks

**Adding a new API endpoint to PreRollTracker:**

1. Choose the appropriate blueprint file (or create a new one)
2. Add the route with `@bp.route()` decorator
3. Add appropriate auth decorator (`@api_or_login_required`)
4. Implement the handler, using `MODEL`, `SETTINGS`, or managers from `tracker_core`
5. Write a test in `tests/test_api.py`

**Adding a new batch field to PreRollTracker:**

1. Add the field to `PreRoll` dataclass in `tracker_core.py`
2. Add the column to `init_db()` in `database.py`
3. Update `_preroll_to_row()` and `_row_to_preroll()` in `database.py`
4. Create a migration in `migrations/versions/` using `_add_column_if_missing()`
5. Update any relevant API endpoints to expose the new field
6. Update HTML pages to display the field

**Adding a new service to ApexAPI:**

1. Create the service class in `services/`
2. Define constructor parameters for dependencies
3. Add initialization to `ServiceContainer.initialize()`
4. Add a typed getter method to `ServiceContainer`
5. Wire event subscriptions if needed in `_setup_event_subscriptions()`
6. Write unit tests with mocked dependencies
7. Inject the service into GUI modules that need it

**Adding a new database table to ApexAPI:**

1. Choose the appropriate repository (or create a new one extending `BaseRepository`)
2. Add the CREATE TABLE statement to `create_tables()`
3. Add indexes for common queries
4. If modifying an existing table, add a migration to `get_migrations()`
5. Write integration tests against a `tmp_path` database

## Environment Variables Reference

### PreRollTracker

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | None (fails on startup) | Flask session encryption key |
| `ADMIN_PASSWORD_HASH` | Yes | None | bcrypt hash of admin password |
| `SENTRY_DSN` | No | "" (disabled) | Sentry error monitoring DSN |
| `SENTRY_ENV` | No | "production" | Sentry environment tag |
| `FLASK_ENV` | No | "production" | Flask environment mode |
| `PORT` | No | 5000 | HTTP port |
| `BACKUP_ENCRYPTION_KEY` | No | None (backups disabled) | AES-256-CBC encryption key |
| `GITHUB_TOKEN` | No | None | GitHub personal access token for backup uploads |
| `PUSHOVER_USER_KEY` | No | None | Pushover user key for notifications |
| `PUSHOVER_APP_TOKEN` | No | None | Pushover app token |

### ApexAPI

ApexAPI uses `apex_config.json` rather than environment variables. The only sensitive item (API token) is stored in the OS keyring. No environment variables are required for normal operation.

## Troubleshooting Common Setup Issues

### PreRollTracker Issues

**"SECURITY ERROR: SECRET_KEY environment variable not set"**

This error occurs at startup when no `.env` file exists or `SECRET_KEY` is missing. Create a `.env` file with a secure random key:

```bash
python -c 'import secrets; print(f"SECRET_KEY={secrets.token_hex(32)}")' >> .env
```

**"bcrypt: error importing module"**

bcrypt requires a C compiler for its native extension. Install build tools for your platform:

```bash
# macOS
xcode-select --install

# Ubuntu/Debian
sudo apt-get install python3-dev build-essential

# Fedora
sudo dnf install python3-devel gcc
```

**"OperationalError: database is locked"**

This occurs when multiple processes try to write simultaneously. Solutions:

- Ensure only one development server instance is running
- Use WAL mode (already enabled in `database.py`)
- If the lock persists after a crash, delete the `-wal` and `-shm` files next to the database

**Port already in use**

If port 5000 is already taken (common on macOS 12+ where AirPlay uses port 5000):

```bash
python app.py  # defaults to 5000
# Change to a different port:
PORT=5001 python app.py
# Or edit run.py to use a different default port
```

**Tests fail with "ModuleNotFoundError"**

Ensure you are running pytest from the project root with the virtual environment activated:

```bash
cd ~/PycharmProjects/PreRollTracker
source venv/bin/activate
pytest
```

### ApexAPI Issues

**"keyring: no suitable backend found"**

On Linux, install a keyring backend:

```bash
pip install keyrings.alt
# or configure GNOME Keyring / KWallet
```

On headless systems or CI, you may need to use the JSON fallback by ensuring keyring is not installed, or mock it in tests.

**"customtkinter: display not found"**

customtkinter requires a display server. On Linux without a desktop environment:

```bash
# Install Xvfb for headless testing
sudo apt-get install xvfb
xvfb-run python apex_gui.py
```

**"aiohttp: connector not available"**

Ensure aiohttp and its dependencies are installed:

```bash
pip install aiohttp asyncio-throttle
```

On some systems, you may also need:

```bash
pip install aiodns  # for faster DNS resolution
```

**API connection failures**

If the Apex Trading API returns errors:

1. Check that your API token is valid: Open the GUI, go to Settings, click "Test Connection"
2. Verify the token has not expired
3. Check your network connection
4. Look at the log output for detailed error messages

The application creates log files in the `logs/` directory when running.

**Build failures with PyInstaller**

Common PyInstaller issues:

```bash
# Missing hidden imports - add to .spec file:
hiddenimports=['customtkinter', 'aiohttp', 'keyring.backends']

# File not found errors - add data files:
datas=[('apex_config_template.json', '.'), ('cache/', 'cache/')]

# Anti-virus false positives (Windows) - sign the executable or add exclusion
```

## Database Management

### PreRollTracker Database Operations

**Creating a backup manually:**

```bash
# Simple file copy (stop the server first for consistency)
cp preroll_tracker.db preroll_tracker.db.backup

# Or use the built-in backup function:
python -c "from database import backup_sqlite_database; backup_sqlite_database('preroll_tracker.db', 'backup.db')"
```

**Restoring from backup:**

```bash
# Stop the server
sudo systemctl stop preroll-tracker

# Replace the database
cp backup.db preroll_tracker.db

# Restart
sudo systemctl start preroll-tracker
```

**Restoring from encrypted backup:**

```bash
openssl enc -d -aes-256-cbc -pbkdf2 \
    -in preroll_tracker.db.backup_YYYYMMDD_HHMMSS.enc \
    -out restored.db \
    -pass pass:"$BACKUP_ENCRYPTION_KEY"
```

**Running a migration manually:**

Migrations run automatically on startup. To force a re-run:

```python
from database import init_db
init_db("preroll_tracker.db")
```

**Inspecting the database:**

```bash
sqlite3 preroll_tracker.db
.tables
.schema batches
SELECT COUNT(*) FROM batches WHERE archived = 0;
.quit
```

### ApexAPI Database Operations

**Inspecting the database:**

```bash
sqlite3 apex_data.db
.tables
.schema orders
SELECT COUNT(*) FROM orders;
.quit
```

**Resetting the database:**

Delete `apex_data.db` and restart the application. All tables will be recreated by the repository initialization code.

**Backing up:**

```python
from repositories.order_repository import OrderRepository
repo = OrderRepository()
repo.backup_database("apex_data_backup.db")
```

## IDE Configuration

### PyCharm Setup

Both projects work well with PyCharm:

1. Open the project directory as a PyCharm project
2. Configure the Python interpreter to use the project's virtual environment
3. Mark the project root as "Sources Root"
4. For PreRollTracker, mark `tests/` as "Test Sources Root"
5. For ApexAPI, mark `tests/` as "Test Sources Root"
6. Set the pytest runner as the default test framework in Settings -> Tools -> Python Integrated Tools

### VS Code Setup

For VS Code:

1. Open the project folder
2. Install the Python extension
3. Select the virtual environment interpreter via the Python: Select Interpreter command
4. Create a `.vscode/settings.json` with:

```json
{
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"],
    "python.linting.enabled": true
}
```

For ApexAPI specifically, add ruff configuration:

```json
{
    "python.linting.ruffEnabled": true,
    "editor.formatOnSave": true,
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff"
    }
}
```

## Google Sheets Integration Setup (ApexAPI)

ApexAPI can sync packing list data with Google Sheets for collaborative access. To set this up:

### Step 1: Create a Google Cloud Project

1. Go to the Google Cloud Console
2. Create a new project or select an existing one
3. Enable the Google Sheets API
4. Create OAuth 2.0 credentials or a Service Account

### Step 2: Configure Credentials

For a service account:

1. Download the JSON key file
2. Place it in the ApexAPI project directory
3. Add the path to `apex_config.json`:

```json
{
    "google_sheets": {
        "credentials_file": "path/to/credentials.json",
        "spreadsheet_id": "your-spreadsheet-id",
        "worksheet_name": "Packing List"
    }
}
```

### Step 3: Share the Spreadsheet

Share the Google Sheet with the service account email address (found in the credentials JSON) with editor permissions.

### Step 4: Enable Sync

In the GUI, open the Google Sheets sync settings and enable automatic synchronization. The `GoogleSheetsSyncService` will handle bidirectional updates between the local database and the shared sheet.

## Pushover Notification Setup (PreRollTracker)

PreRollTracker can send push notifications via Pushover for backup failures and other alerts.

### Step 1: Create a Pushover Account

1. Sign up at pushover.net
2. Note your User Key from the dashboard

### Step 2: Create an Application

1. Create a new application in Pushover
2. Note the Application Token

### Step 3: Configure Environment Variables

Add to your `.env` file:

```bash
PUSHOVER_USER_KEY=your-user-key-here
PUSHOVER_APP_TOKEN=your-app-token-here
```

### Step 4: Configure via API

Use the settings API endpoints:

```bash
# View current settings
curl -H "X-API-Key: your-key" https://himomstats.online/api/pushover/settings

# Update settings
curl -X PUT -H "X-API-Key: your-key" -H "Content-Type: application/json" \
    -d '{"user_key": "...", "app_token": "...", "enabled": true}' \
    https://himomstats.online/api/pushover/settings

# Send a test notification
curl -X POST -H "X-API-Key: your-key" \
    https://himomstats.online/api/pushover/test
```

## Sentry Monitoring Setup (PreRollTracker)

### Configuration

Sentry is configured in `app.py` at startup. The only required value is `SENTRY_DSN`:

```bash
SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0
```

### What Gets Tracked

- Unhandled exceptions in Flask request handlers
- Performance traces (5% sampling)
- Profiles (5% sampling)
- Release tracking via git commit SHA

### What Gets Filtered Out

The `before_send` callback filters out common noise:

- `ConnectionReset` errors (client disconnected)
- `BrokenPipe` errors (client closed connection mid-response)
- `Timeout` errors (external service timeouts)

PII is never sent (`send_default_pii=False`).

## Production Deployment Checklist

### PreRollTracker Production Checklist

Before deploying to production, verify:

1. `SECRET_KEY` is a strong random value (at least 32 bytes hex)
2. `ADMIN_PASSWORD_HASH` is set with a bcrypt hash
3. `SENTRY_DSN` is configured for error monitoring
4. `BACKUP_ENCRYPTION_KEY` is set for encrypted backups
5. `GITHUB_TOKEN` is set if using GitHub Releases for off-site backups
6. The `.env` file has restrictive permissions (`chmod 600 .env`)
7. Gunicorn is configured with appropriate worker count (2-4 for typical load)
8. Nginx is configured as a reverse proxy with SSL termination
9. The database file has appropriate filesystem permissions
10. Log rotation is configured (10 MB files, 10 backups)
11. The `data/` and `backups/` directories exist with proper permissions
12. `FLASK_ENV=production` is set for secure cookie settings

### ApexAPI Distribution Checklist

Before distributing a new build:

1. Run the full test suite: `pytest`
2. Run the linter: `ruff check .`
3. Update the version number if applicable
4. Build with PyInstaller: `python build_exe.py`
5. Test the built executable on a clean machine
6. Verify that configuration files are created correctly on first run
7. Check that the keyring integration works on the target platform
8. Verify API connectivity from the built application
9. Test printing functionality on the target platform
