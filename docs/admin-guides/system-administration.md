# System Administration Guide

## Overview

This guide covers the day-to-day administration of PreRollTracker (the web-based production dashboard at himomstats.online) and ApexAPI (the desktop application for order management and inventory sync). It is written for system administrators who are comfortable with computers but do not need to write code.

Both applications share a single-admin-password authentication model. PreRollTracker runs as a web server, while ApexAPI runs as a standalone Windows desktop application. This guide walks through user management, API key management, recovery key setup, monitoring, and rate limiting.

---

## 1. User Management

### 1.1 Understanding the Authentication Model

PreRollTracker uses a **single admin password** model. There is one password that grants full access to the admin dashboard. There are no individual user accounts or role-based access levels.

- The password is stored as a **bcrypt hash** in the server's `.env` file (environment variable `ADMIN_PASSWORD_HASH`).
- When someone logs in, the password they type is hashed and compared against the stored hash. The actual password is never stored in plain text.
- Sessions last 30 days by default when "Remember Me" is checked, or until the browser is closed if it is not.
- Session cookies are HTTP-only and marked Secure in production to prevent theft.

| Authentication Feature | Details |
|---|---|
| Password storage | bcrypt hash in `.env` file |
| Session duration | 30 days (with "Remember Me") |
| Session cookie flags | HttpOnly, Secure (production), SameSite=Lax |
| CSRF protection | Enabled via Flask-WTF, tokens live as long as the session |
| Max upload size | 16 MB |

[SCREENSHOT: PreRollTracker login page showing the password field, Remember Me checkbox, and Forgot Password link]

### 1.2 Changing the Admin Password

There are two ways to change the admin password: from the command line, or from the web-based settings page.

#### Method 1: Command-Line Script (Recommended for Initial Setup)

Use the standalone password setup script. This does not require the Flask application to be running.

1. SSH into the server where PreRollTracker is installed.
2. Navigate to the application directory:
   ```
   cd /opt/preroll-tracker
   ```
3. Activate the virtual environment:
   ```
   source venv/bin/activate
   ```
4. Run the password setup script:
   ```
   python3 setup_password_standalone.py
   ```
5. The script will prompt you to either enter a custom password or press Enter to auto-generate a secure one.
6. If you type a custom password, you will be asked to confirm it.
7. The script outputs the bcrypt hash and offers to write it directly to the `.env` file.
8. If the `.env` file already contains `ADMIN_PASSWORD_HASH`, the script asks for confirmation before overwriting.
9. Restart the application for the change to take effect:
   ```
   sudo systemctl restart preroll-tracker
   ```

**Important:** If you choose to auto-generate a password, write it down immediately. The generated password is shown only once and cannot be recovered later.

#### Method 2: Settings Page (From the Web Interface)

1. Log in to the PreRollTracker admin dashboard.
2. Navigate to **Settings**.
3. Find the **Change Password** section.
4. Enter a new password and confirm it.
5. Click **Save**. The new password takes effect immediately for future logins (your current session remains active).

[SCREENSHOT: PreRollTracker settings page showing the Change Password section with new password and confirm password fields]

### 1.3 What Happens if You Forget the Password

If you forget the admin password and have a recovery key configured, you can reset it through the web interface at `/forgot-password`. See Section 3 below for recovery key details.

If you do not have a recovery key, you must use the command-line method described in Method 1 above, which requires SSH access to the server.

---

## 2. Managing API Keys

### 2.1 What the API Key Is For

PreRollTracker generates a unique API key that external programs (like ApexAPI) use to interact with the dashboard programmatically. The API key is sent in the `X-API-Key` HTTP header with every API request.

This is different from the admin password:
- The **admin password** is for human users logging in through a web browser.
- The **API key** is for software programs that talk to PreRollTracker's API endpoints.

| Feature | Admin Password | API Key |
|---|---|---|
| Used by | Humans via browser | Software programs |
| Sent via | Login form (POST body) | `X-API-Key` HTTP header |
| Storage | bcrypt hash in `.env` | Plain text in database settings |
| Regeneration | Manual password change | One-click regeneration |

### 2.2 Viewing the Current API Key

1. Log in to the PreRollTracker admin dashboard.
2. Navigate to **Settings**.
3. The API key is displayed in the **API Configuration** section.
4. You can also retrieve it programmatically:
   ```
   curl -H "X-API-Key: YOUR_CURRENT_KEY" https://himomstats.online/api/api-key
   ```

The API key is auto-generated the first time it is requested. It is a 32-character URL-safe token.

[SCREENSHOT: PreRollTracker settings page showing the API Key section with the key displayed and a Regenerate button]

### 2.3 Regenerating the API Key

If you suspect the API key has been compromised, regenerate it immediately:

1. Log in to the PreRollTracker admin dashboard.
2. Navigate to **Settings**.
3. Click **Regenerate API Key**.
4. The old key is invalidated immediately. Any program using the old key will stop working.
5. Copy the new key and update it in all programs that use it (particularly ApexAPI's `apex_config.json` file, in the `dashboard_api_key` field).

**Warning:** Regenerating the API key breaks all existing integrations until they are updated with the new key. Plan to update ApexAPI's configuration immediately after regeneration.

### 2.4 How API Key Authentication Works

When a request includes the `X-API-Key` header, PreRollTracker compares the provided key against the stored key using a constant-time comparison (to prevent timing attacks). If the key matches, the request is allowed. If not, a 401 Unauthorized response is returned.

API key authentication bypasses CSRF protection, since it is designed for programmatic access. Browser-based sessions still require CSRF tokens.

---

## 3. Recovery Key Setup and Usage

### 3.1 What Is a Recovery Key?

A recovery key is a backup credential you can use to reset the admin password if you forget it. It follows the format:

```
HARVEST-XXXX-XXXX-XXXX
```

Where `XXXX` represents groups of random uppercase letters and digits. The recovery key is hashed with bcrypt and stored in the database, just like the admin password. The plain-text key is shown only once when generated.

### 3.2 Setting Up a Recovery Key

Recovery keys are generated in two scenarios:

1. **During password reset:** After you successfully reset the admin password using a recovery key, a new recovery key is automatically generated and displayed.
2. **Through the settings page:** You can generate a recovery key from the admin dashboard settings.

**Steps to set up a recovery key from settings:**

1. Log in to the PreRollTracker admin dashboard.
2. Navigate to **Settings**.
3. Find the **Recovery Key** section.
4. Click **Generate Recovery Key**.
5. A key in the format `HARVEST-XXXX-XXXX-XXXX` is displayed.
6. **Write this key down on paper or store it in a secure password manager.** It will not be shown again.

### 3.3 Using a Recovery Key

1. Go to the PreRollTracker login page.
2. Click **Forgot Password**.
3. If no recovery key is configured, you will see a message indicating that. Use the command-line method instead.
4. Enter your recovery key in the field and submit.
5. If valid, you are given a time-limited (10-minute) session to set a new password.
6. Enter and confirm a new password.
7. A **new recovery key** is generated and displayed. Save it immediately since the old one is now invalid.

[SCREENSHOT: Forgot Password page showing the recovery key input field]

---

## 4. Setting Up ApexAPI Tokens

### 4.1 Apex Trading API Token

ApexAPI connects to the Apex Trading platform to pull order data. It authenticates with a Bearer token.

1. Log in to your Apex Trading account at `https://app.apextrading.com`.
2. Navigate to your account settings or API access section.
3. Generate a personal access token.
4. Open the `apex_config.json` file in the ApexAPI installation directory.
5. Set the `api_token` field to your token:
   ```
   "api_token": "130|xEkXWyHGBWUb46HQA8UsQKrTUwCaJq33tmPRXwUH"
   ```
6. Save the file and restart ApexAPI.
7. The application will validate the token on startup by calling the `/api/v1/welcome` endpoint.

### 4.2 Dashboard API Key (PreRollTracker Connection)

ApexAPI also connects to PreRollTracker's API for inventory sync and batch data.

1. Log in to PreRollTracker and copy the API key from the Settings page (see Section 2.2).
2. Open `apex_config.json` in the ApexAPI directory.
3. Set the `dashboard_api_key` field:
   ```
   "dashboard_api_key": "45cf0a80-7502-4cbb-884d-83875fbc2190"
   ```
4. Save the file and restart ApexAPI.
5. ApexAPI connects to `https://himomstats.online` by default and sends the key via the `X-API-Key` header.

[SCREENSHOT: ApexAPI settings showing the Dashboard API Key field with a Test Connection button]

### 4.3 Verifying Token Connectivity

After configuring both tokens, verify connectivity:

1. Open ApexAPI.
2. Check the status indicators in the application. They should show green for both Apex Trading and Dashboard connections.
3. If a connection fails, check the `logs/` directory in the ApexAPI folder for detailed error messages.

---

## 5. Monitoring System Health

### 5.1 Backup Status

PreRollTracker has a built-in backup health check endpoint:

```
GET https://himomstats.online/api/backup-status
```

This returns a JSON payload with:

| Field | Description |
|---|---|
| `last_backup_time` | Timestamp of the most recent backup |
| `last_backup_size_bytes` | Size of the most recent backup file |
| `local_backup_count` | Number of local backup files on disk |
| `remote_backup_count` | Number of backup releases on GitHub |
| `last_remote_tag` | Git tag of the most recent remote backup |
| `last_status` | `success`, `failed`, or `never_run` |
| `last_error` | Error message if the last backup failed |

Backups run automatically every **6 hours**. If `last_status` shows `failed`, check the application logs and verify that environment variables (`BACKUP_ENCRYPTION_KEY`, `GITHUB_REPO`) are set correctly.

### 5.2 Sentry Error Tracking

PreRollTracker integrates with Sentry for real-time error monitoring. Sentry captures unhandled exceptions and sends alerts.

- **Dashboard:** Log in to your Sentry project to view error reports.
- **Configuration:** The Sentry DSN is set via the `SENTRY_DSN` environment variable in the `.env` file.
- **Traces:** Sampling rates are set to 5% for both transaction traces and profiles to minimize performance impact.
- **Filtering:** Connection resets, broken pipes, and timeout errors are automatically filtered out to reduce noise.

If Sentry shows a spike in errors, check the application logs at `/opt/preroll-tracker/logs/preroll_tracker.log` for additional context.

### 5.3 Application Logs

PreRollTracker writes logs to two locations:

1. **Application log file:** `logs/preroll_tracker.log` (rotating, 10 MB max, 10 backup files).
2. **systemd journal:** View with `sudo journalctl -u preroll-tracker -f`.

ApexAPI writes logs to the `logs/` directory in its installation folder. Log level is configurable in `apex_config.json` via the `log_level` field (default: `INFO`).

### 5.4 Service Health Checks

To check if PreRollTracker is running:

```
sudo systemctl status preroll-tracker
```

To view live logs:

```
sudo journalctl -u preroll-tracker -f
```

To check the nginx reverse proxy:

```
sudo systemctl status nginx
sudo nginx -t
```

---

## 6. Rate Limiting Configuration

### 6.1 How Rate Limiting Works

PreRollTracker uses Flask-Limiter to protect against brute-force attacks and API abuse. Rate limits are applied per IP address using the `get_remote_address` function.

The application is configured with **no global default limits**, but specific routes have their own limits:

| Route | Limit | Purpose |
|---|---|---|
| `/login` (POST) | Implicit via session | Prevent brute-force password guessing |
| `/forgot-password` (POST) | 2 per minute | Prevent recovery key brute-force |
| `/reset-password` (POST) | 5 per minute | Prevent password reset abuse |
| API endpoints | No explicit limit | Protected by API key requirement |

### 6.2 Adjusting Rate Limits

Rate limits are defined in the application code (not in configuration files). To change them, a developer would need to modify the Flask route decorators. As an administrator, you should be aware of these limits but typically do not need to change them.

If legitimate users are hitting rate limits (for example, if they are locked out after too many failed login attempts), you can:

1. Wait for the limit window to reset (usually 1 minute).
2. Restart the application, which clears in-memory rate limit counters:
   ```
   sudo systemctl restart preroll-tracker
   ```

### 6.3 IP Address Detection Behind Nginx

Since PreRollTracker runs behind an nginx reverse proxy, the real client IP is forwarded via the `X-Real-IP` and `X-Forwarded-For` headers. The nginx configuration sets these headers automatically:

```
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

Flask-Limiter uses `get_remote_address` to extract the correct IP. If you change the proxy setup, ensure these headers are still being forwarded correctly, or all rate limits will apply to the proxy's IP instead of individual clients.

---

## 7. Common Administrative Tasks

### 7.1 Restarting Services

**PreRollTracker:**
```
sudo systemctl restart preroll-tracker
```

**Nginx:**
```
sudo systemctl restart nginx
```

### 7.2 Checking Active Batches

Use the management script on the server:
```
cd /opt/preroll-tracker
source venv/bin/activate
python3 manage.py status
python3 manage.py list-batches
```

### 7.3 Creating a Manual Backup

```
cd /opt/preroll-tracker
source venv/bin/activate
python3 manage.py backup
```

### 7.4 Viewing Audit Logs

Audit logs track every change to batch data (field changes, status transitions, inventory updates). They are stored in the `audit_log` table of the SQLite database. You can view them through the admin dashboard or query the database directly:

```
sqlite3 preroll_tracker.db "SELECT ts, batch, strain, field, old, new FROM audit_log ORDER BY ts DESC LIMIT 20;"
```

---

## 8. Security Best Practices

1. **Use strong passwords.** The auto-generated passwords from `setup_password_standalone.py` are 16+ character URL-safe tokens. Use them when possible.
2. **Store the recovery key securely.** Write it on paper and store it in a locked location, or use a password manager.
3. **Regenerate the API key periodically.** Even if it has not been compromised, rotating keys is good practice.
4. **Keep the `.env` file restricted.** Only the application user should be able to read it:
   ```
   chmod 600 /opt/preroll-tracker/.env
   ```
5. **Monitor Sentry alerts.** Investigate any unusual error patterns immediately.
6. **Keep software updated.** Regularly update Python dependencies and the operating system.
7. **Use HTTPS in production.** The application enforces secure cookies when `FLASK_ENV=production`, which requires HTTPS to function correctly.

---

## Summary

| Task | How |
|---|---|
| Change admin password (CLI) | `python3 setup_password_standalone.py` then restart |
| Change admin password (web) | Settings > Change Password |
| View API key | Settings > API Configuration |
| Regenerate API key | Settings > Regenerate API Key |
| Set up recovery key | Settings > Generate Recovery Key |
| Reset forgotten password | `/forgot-password` with recovery key |
| Check backup health | `GET /api/backup-status` |
| View error reports | Sentry dashboard |
| Restart application | `sudo systemctl restart preroll-tracker` |
| Check service status | `sudo systemctl status preroll-tracker` |
