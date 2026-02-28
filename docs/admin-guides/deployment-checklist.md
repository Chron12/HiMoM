# Deployment Checklist

## Overview

This guide provides step-by-step instructions for deploying PreRollTracker (the web application) and ApexAPI (the desktop application). PreRollTracker is deployed on a Linux server (Ubuntu recommended) behind an nginx reverse proxy. ApexAPI is built as a standalone Windows executable and distributed to user workstations.

Follow each section in order. Each step includes verification commands so you can confirm success before moving on.

---

## Part 1: PreRollTracker Deployment

### 1.1 Server Requirements

Before starting, confirm your server meets these requirements:

| Requirement | Minimum | Recommended |
|---|---|---|
| Operating System | Ubuntu 20.04 LTS | Ubuntu 22.04 LTS or newer |
| RAM | 1 GB | 2 GB |
| Disk Space | 5 GB | 20 GB (for backups) |
| Python | 3.8+ | 3.10+ |
| Network | Port 80 and 443 open | Static IP or domain name |
| Domain | Optional | Required for SSL/HTTPS |

### 1.2 Python Environment Setup

1. SSH into your server.

2. Update the system packages:
   ```
   sudo apt update && sudo apt upgrade -y
   ```

3. Install Python and required system packages:
   ```
   sudo apt install -y python3 python3-pip python3-venv nginx git curl
   ```

4. Verify Python version:
   ```
   python3 --version
   ```
   Expected output: `Python 3.10.x` or higher.

5. Create the application directory:
   ```
   sudo mkdir -p /opt/preroll-tracker
   sudo chown $USER:$USER /opt/preroll-tracker
   ```

6. Copy the application files to the server. You can use `scp`, `rsync`, or `git clone`:
   ```
   # Option A: Using git
   git clone https://github.com/your-repo/preroll-tracker.git /opt/preroll-tracker

   # Option B: Using rsync from your local machine
   rsync -avz --exclude='venv' --exclude='__pycache__' ./PreRollTracker/ user@server:/opt/preroll-tracker/
   ```

7. Create a Python virtual environment:
   ```
   cd /opt/preroll-tracker
   python3 -m venv venv
   ```

8. Activate the virtual environment and install dependencies:
   ```
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

9. Verify installation:
   ```
   python3 -c "import flask; import bcrypt; import sentry_sdk; print('All dependencies OK')"
   ```

**Verification:** You should see `All dependencies OK` with no import errors.

[SCREENSHOT: Terminal showing successful pip install output with all dependencies installed]

### 1.3 Environment Variables Configuration

1. Create the `.env` file:
   ```
   nano /opt/preroll-tracker/.env
   ```

2. Add the following variables (replace placeholder values with your actual values):

   ```
   FLASK_ENV=production
   SECRET_KEY=your-generated-secret-key-here
   ADMIN_PASSWORD_HASH=your-bcrypt-hash-here
   SENTRY_DSN=your-sentry-dsn-or-leave-empty
   SENTRY_ENV=production
   BACKUP_ENCRYPTION_KEY=your-long-random-encryption-passphrase
   GITHUB_REPO=your-username/your-repo
   PUSHOVER_APP_TOKEN=your-pushover-token-or-leave-empty
   LOG_LEVEL=INFO
   ```

3. Generate the SECRET_KEY:
   ```
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```
   Copy the output and paste it as the `SECRET_KEY` value.

4. Generate the admin password hash:
   ```
   cd /opt/preroll-tracker
   source venv/bin/activate
   python3 setup_password_standalone.py
   ```
   Follow the prompts. The script will offer to write the hash to `.env` automatically.

5. Generate the BACKUP_ENCRYPTION_KEY:
   ```
   python3 -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

6. Secure the `.env` file:
   ```
   chmod 600 /opt/preroll-tracker/.env
   ```

**Verification:** Run `cat /opt/preroll-tracker/.env` and confirm all variables are populated. The `SECRET_KEY` should be at least 64 hexadecimal characters. The `ADMIN_PASSWORD_HASH` should start with `$2b$12$`.

### 1.4 Database Initialization

The database is created automatically when the application first starts. However, you can initialize it manually:

1. Activate the virtual environment:
   ```
   cd /opt/preroll-tracker
   source venv/bin/activate
   ```

2. Initialize the database:
   ```
   python3 -c "from database import init_db; init_db('preroll_tracker.db'); print('Database initialized')"
   ```

3. Verify the database was created:
   ```
   ls -la preroll_tracker.db
   sqlite3 preroll_tracker.db ".tables"
   ```
   Expected output should include tables: `batches`, `audit_log`, `finished_goods`, `settings`, and others.

4. Create the required directories:
   ```
   mkdir -p logs backups data
   ```

**Verification:** `sqlite3 preroll_tracker.db ".tables"` lists all expected tables.

### 1.5 Gunicorn Startup

1. Test that the application starts correctly:
   ```
   cd /opt/preroll-tracker
   source venv/bin/activate
   gunicorn -w 1 -b 127.0.0.1:5000 run:app --timeout 30
   ```
   Open another terminal and test: `curl http://127.0.0.1:5000/login`
   You should see HTML content. Press Ctrl+C to stop the test server.

2. Create the systemd service file:
   ```
   sudo nano /etc/systemd/system/preroll-tracker.service
   ```

3. Paste the following configuration:
   ```
   [Unit]
   Description=Pre-Roll Tracker Web Application
   After=network.target

   [Service]
   Type=exec
   User=your-username
   Group=your-username
   WorkingDirectory=/opt/preroll-tracker
   Environment=PATH=/opt/preroll-tracker/venv/bin
   ExecStart=/opt/preroll-tracker/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 run:app
   ExecReload=/bin/kill -s HUP $MAINPID
   Restart=always
   RestartSec=3

   [Install]
   WantedBy=multi-user.target
   ```
   Replace `your-username` with the actual Linux user who owns the application files.

4. Enable and start the service:
   ```
   sudo systemctl daemon-reload
   sudo systemctl enable preroll-tracker
   sudo systemctl start preroll-tracker
   ```

5. Check the service status:
   ```
   sudo systemctl status preroll-tracker
   ```

**Verification:** The status should show `active (running)`. Run `curl http://127.0.0.1:5000/login` and confirm you get HTML content.

[SCREENSHOT: Terminal showing systemctl status output with "active (running)" status]

### 1.6 Nginx Reverse Proxy Configuration

1. Create the nginx site configuration:
   ```
   sudo nano /etc/nginx/sites-available/preroll-tracker
   ```

2. Paste the following configuration:
   ```
   server {
       listen 80;
       server_name himomstats.online www.himomstats.online;

       location / {
           proxy_pass http://127.0.0.1:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```
   Replace `himomstats.online` with your domain name, or use `server_name _;` to accept any hostname.

3. Enable the site and disable the default:
   ```
   sudo ln -sf /etc/nginx/sites-available/preroll-tracker /etc/nginx/sites-enabled/
   sudo rm -f /etc/nginx/sites-enabled/default
   ```

4. Test the nginx configuration:
   ```
   sudo nginx -t
   ```
   Expected output: `syntax is ok` and `test is successful`.

5. Restart nginx:
   ```
   sudo systemctl restart nginx
   ```

**Verification:** Open a web browser and navigate to `http://your-server-ip`. You should see the PreRollTracker login page.

### 1.7 SSL/HTTPS Setup

HTTPS is strongly recommended for production. The easiest method is Certbot with Let's Encrypt.

1. Install Certbot:
   ```
   sudo apt install -y certbot python3-certbot-nginx
   ```

2. Obtain and install the certificate:
   ```
   sudo certbot --nginx -d himomstats.online -d www.himomstats.online
   ```
   Follow the prompts. Certbot will:
   - Verify domain ownership.
   - Obtain the SSL certificate.
   - Automatically modify the nginx configuration.
   - Set up automatic renewal.

3. Verify the certificate:
   ```
   sudo certbot certificates
   ```

4. Test automatic renewal:
   ```
   sudo certbot renew --dry-run
   ```

5. Verify HTTPS works: Open `https://himomstats.online` in a browser. You should see the lock icon and the login page.

**Verification:** `curl -I https://himomstats.online` should return `HTTP/2 200` with no SSL errors.

[SCREENSHOT: Browser address bar showing the lock icon and https://himomstats.online]

### 1.8 Backup System Verification

After deployment, verify the backup system is working:

1. Check that backup environment variables are set:
   ```
   grep BACKUP /opt/preroll-tracker/.env
   grep GITHUB /opt/preroll-tracker/.env
   ```

2. Verify the `gh` CLI is installed and authenticated:
   ```
   gh auth status
   ```
   If not installed: `sudo apt install -y gh` then `gh auth login`.

3. Verify OpenSSL is installed:
   ```
   openssl version
   ```

4. Trigger a manual backup to test:
   ```
   cd /opt/preroll-tracker
   source venv/bin/activate
   python3 -c "from backup_manager import BackupManager; bm = BackupManager(); print(bm.run_full_backup_cycle())"
   ```

5. Check the backup status endpoint:
   ```
   curl https://himomstats.online/api/backup-status
   ```
   Verify `last_status` is `success`.

6. Check GitHub for the backup release:
   ```
   gh release list --repo your-username/your-repo --limit 5
   ```

**Verification:** The backup status shows `success`, a local backup file exists in `backups/`, and a GitHub release has been created.

### 1.9 Post-Deployment Checklist

Run through this checklist to confirm everything is working:

| Check | Command | Expected Result |
|---|---|---|
| Application running | `sudo systemctl status preroll-tracker` | `active (running)` |
| Nginx running | `sudo systemctl status nginx` | `active (running)` |
| Login page loads | `curl -s https://himomstats.online/login` | HTML content |
| Admin login works | Log in via browser | Dashboard loads |
| API responds | `curl https://himomstats.online/api/overview` | JSON with batch count |
| Backup system | `curl https://himomstats.online/api/backup-status` | `"last_status": "success"` |
| Sentry connected | Check Sentry dashboard | Startup event visible |
| SSL certificate valid | `curl -I https://himomstats.online` | `HTTP/2 200` |
| Logs being written | `ls -la /opt/preroll-tracker/logs/` | Log file exists with recent timestamp |

---

## Part 2: ApexAPI Deployment

### 2.1 Building the Windows Executable

ApexAPI is distributed as a standalone Windows `.exe` file built with PyInstaller. The build process is performed on a Windows development machine.

**Prerequisites on the build machine:**

- Python 3.10+ installed.
- All dependencies from `requirements.txt` installed in a virtual environment.
- PyInstaller installed: `pip install pyinstaller`

**Build Steps:**

1. Open a Command Prompt or PowerShell in the ApexAPI project directory.

2. Activate the virtual environment:
   ```
   venv\Scripts\activate
   ```

3. Run the clean build script:
   ```
   python build_exe.py
   ```

   This script performs three steps:
   - **Cleans** all cached build artifacts (`build/`, `__pycache__/`, `.pyc` files).
   - **Verifies imports** to ensure all critical modules can be loaded.
   - **Runs PyInstaller** using the `apex_gui.spec` configuration file.

4. Wait for the build to complete. This typically takes 2-5 minutes.

5. On success, the executable is located at:
   ```
   dist\ApexTradingGUI.exe
   ```

**Verification:** The console output shows `BUILD SUCCESSFUL!` and the file `dist/ApexTradingGUI.exe` exists.

[SCREENSHOT: Build script output showing the three build phases completing successfully]

### 2.2 What the Build Includes

The PyInstaller spec file (`apex_gui.spec`) bundles the following into the executable:

| Component | Description |
|---|---|
| Application code | All Python modules from `gui/`, `api/`, `services/`, `repositories/`, `events/`, `cache/`, `security/` |
| Configuration files | `apex_config.json`, `order_form_config.json`, `inventory_cache.json`, `printed_orders.json` |
| GUI framework | customtkinter themes and assets |
| Dependencies | requests, pandas, numpy, reportlab, openpyxl, aiohttp, keyring, cryptography, PIL |

**Excluded from the build** (to reduce file size): matplotlib, scipy, IPython, jupyter, pytest, setuptools, pip.

The resulting `.exe` is a **single file** that includes all dependencies. No Python installation is required on the target machine.

### 2.3 Distributing to Users

1. Copy `dist/ApexTradingGUI.exe` to a shared network drive or USB drive.

2. Also copy the following configuration files alongside the `.exe`:
   - `apex_config.json` (pre-configured with appropriate defaults)
   - `order_form_config.json`

3. On the target Windows machine, create a folder for the application:
   ```
   C:\ApexTrading\
   ```

4. Copy the `.exe` and configuration files into this folder.

5. Create a desktop shortcut to `ApexTradingGUI.exe` for easy access.

**Important:** The `.exe`, `apex_config.json`, and other configuration files must be in the **same directory**. The application looks for config files relative to the `.exe` location.

### 2.4 First-Time Configuration

When ApexAPI runs for the first time on a new machine, the following setup is needed:

1. **Launch the application** by double-clicking `ApexTradingGUI.exe`.

2. **Set the Apex Trading API token:**
   - Close the application.
   - Open `apex_config.json` in a text editor (right-click > Edit with Notepad).
   - Set the `api_token` field to the Apex Trading bearer token.
   - Save the file.
   - Relaunch the application.

3. **Set the Dashboard API key:**
   - In `apex_config.json`, set the `dashboard_api_key` field.
   - Save and relaunch.

4. **Select a printer:**
   - In the application, go to settings or the print dialog.
   - Select the correct printer from the dropdown.
   - This is saved to `apex_config.json` automatically.

5. **Configure the license number (optional):**
   - Set `license_number` in `apex_config.json` for compliance display.

6. **Verify connections:**
   - After configuration, the application should show green status indicators for both Apex Trading and Dashboard connections.
   - If either shows red, check the corresponding token/key.

[SCREENSHOT: ApexAPI first-time setup showing the connection status indicators for Apex Trading (green) and Dashboard (green)]

### 2.5 Verifying API Connectivity

After first-time configuration, verify both API connections:

**Apex Trading API:**

1. The application automatically validates the token on startup by calling `GET /api/v1/welcome`.
2. If the token is invalid, you will see an error message in the application.
3. Check the logs in the `logs/` folder for details.

**PreRollTracker Dashboard API:**

1. The application tests the connection by calling `GET /api/overview` on PreRollTracker.
2. A successful connection returns the number of active batches.
3. If it fails, verify:
   - The `dashboard_api_key` matches what is in PreRollTracker Settings.
   - The server `https://himomstats.online` is accessible from this machine.
   - No firewall is blocking HTTPS (port 443) traffic.

**Quick connectivity test from the Windows machine:**

Open a web browser and navigate to `https://himomstats.online`. If the page loads, the network path is clear.

### 2.6 File Structure After Installation

After installation and first run, the ApexAPI directory should contain:

```
C:\ApexTrading\
    ApexTradingGUI.exe          -- Main application
    apex_config.json            -- Configuration (tokens, settings)
    order_form_config.json      -- Order form column mappings
    apex_data.db                -- SQLite database (created on first run)
    inventory_cache.json        -- Cached inventory (created on first sync)
    printed_orders.json         -- Print history (created on first print)
    third_party_orders_cache.json -- Third-party cache (created on first sync)
    cache/                      -- API response cache directory
    logs/                       -- Application log files
```

### 2.7 Updating ApexAPI

To deploy a new version:

1. Close ApexAPI on all workstations.
2. Build the new `.exe` (see Section 2.1).
3. Replace the old `ApexTradingGUI.exe` with the new one.
4. **Do not replace** `apex_config.json` unless the configuration format has changed. The existing config preserves user settings.
5. Relaunch the application.

If the configuration format has changed between versions:

1. Back up the existing `apex_config.json`.
2. Copy the new `apex_config_template.json` as `apex_config.json`.
3. Re-enter the `api_token` and `dashboard_api_key` from the backup.
4. Adjust other settings as needed.

---

## Part 3: Post-Deployment Verification

### 3.1 End-to-End Integration Test

After both applications are deployed, run this end-to-end test:

1. **Create a test batch in PreRollTracker:**
   - Log in to the admin dashboard.
   - Create a new batch with a known strain name.
   - Move it through a few production stages.
   - Verify it appears in the API: `curl -H "X-API-Key: YOUR_KEY" https://himomstats.online/api/data`

2. **Verify ApexAPI can read it:**
   - Open ApexAPI.
   - Check the dashboard connection status.
   - If batch sync is enabled, the log should show the new batch's strain in the mapping.

3. **Verify order flow:**
   - Create a test order in Apex Trading (or wait for a real order).
   - Verify it appears in ApexAPI's order list.
   - If the order contains pre-roll products, verify the batch sync correctly maps quantities.

4. **Verify backup:**
   - Wait for the next automatic backup cycle (every 6 hours), or trigger manually.
   - Check `/api/backup-status` to confirm success.

### 3.2 Monitoring After Deployment

For the first 48 hours after deployment, monitor:

| What to Watch | How | Healthy Sign |
|---|---|---|
| Application uptime | `sudo systemctl status preroll-tracker` | Running continuously |
| Error rate | Sentry dashboard | No new errors |
| Backup success | `curl /api/backup-status` | `"last_status": "success"` |
| API response time | Browser developer tools | Pages load in under 2 seconds |
| Disk space | `df -h` | At least 5 GB free |
| Memory usage | `free -h` | At least 500 MB available |
| ApexAPI sync | Check sync status in ApexAPI | Green indicators, no errors |

### 3.3 Rollback Plan

If the deployment fails and you need to roll back:

**PreRollTracker:**

1. Stop the service: `sudo systemctl stop preroll-tracker`
2. Restore the previous code from your backup or version control.
3. Restore the database from backup if needed (see Data Management Guide).
4. Restart the service: `sudo systemctl start preroll-tracker`

**ApexAPI:**

1. Close the application.
2. Replace the `.exe` with the previous version.
3. If the database is corrupted, delete `apex_data.db`. It will be rebuilt on next launch.
4. Relaunch.

---

## Quick Reference

### PreRollTracker Server Commands

| Action | Command |
|---|---|
| Start | `sudo systemctl start preroll-tracker` |
| Stop | `sudo systemctl stop preroll-tracker` |
| Restart | `sudo systemctl restart preroll-tracker` |
| Status | `sudo systemctl status preroll-tracker` |
| View logs | `sudo journalctl -u preroll-tracker -f` |
| View app log | `tail -f /opt/preroll-tracker/logs/preroll_tracker.log` |
| Restart nginx | `sudo systemctl restart nginx` |
| Test nginx config | `sudo nginx -t` |
| Check SSL cert | `sudo certbot certificates` |
| Renew SSL cert | `sudo certbot renew` |
| Manual backup | `cd /opt/preroll-tracker && source venv/bin/activate && python3 manage.py backup` |

### ApexAPI Windows Reference

| Action | How |
|---|---|
| Launch | Double-click `ApexTradingGUI.exe` |
| Edit config | Open `apex_config.json` in Notepad |
| View logs | Open the `logs/` folder |
| Clear cache | Delete contents of `cache/` folder |
| Reset database | Delete `apex_data.db` (recreated on restart) |
| Update | Replace `ApexTradingGUI.exe` with new version |

### Key File Locations

| File | PreRollTracker Location | ApexAPI Location |
|---|---|---|
| Configuration | `/opt/preroll-tracker/.env` | `apex_config.json` (same dir as `.exe`) |
| Database | `/opt/preroll-tracker/preroll_tracker.db` | `apex_data.db` (same dir as `.exe`) |
| Logs | `/opt/preroll-tracker/logs/` | `logs/` (same dir as `.exe`) |
| Backups | `/opt/preroll-tracker/backups/` | N/A (data is rebuildable) |
