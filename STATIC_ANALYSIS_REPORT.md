# WatchMan NIDS - Static Analysis Report

**Date:** 2026-06-15
**Phase:** 3 - Static Code Analysis

## 1. Objective
Identify and document any runtime risks, logical errors, and security vulnerabilities (e.g., hardcoded secrets, SQL injection vectors, broken access control) within the WatchMan codebase.

## 2. Security Posture

### 2.1 Hardcoded Secrets & Credentials
*   **⚠️ WARNING:** `src/watchman_config.py` contains default fallback values for `jwt_secret` (`change-this-watchman-secret-before-production`) and `admin_password` (`watchman2026`). While these can be overridden via the `WATCHMAN_JWT_SECRET` environment variable, they pose a risk if deployed to production without configuration changes.
*   **⚠️ WARNING:** `src/cli.py` hardcodes the default bootstrap admin password as `watchman2026`.
*   **✅ PASS:** `src/anchoring.py` correctly enforces the use of the `WATCHMAN_PRIVATE_KEY` environment variable when blockchain functionality is enabled, avoiding hardcoded private keys.

### 2.2 SQL Injection (SQLi)
*   **✅ PASS:** An audit of `src/db.py` confirms that all database queries (e.g., `INSERT`, `SELECT`, `UPDATE`) use SQLite's parameter substitution (`?`). This effectively neutralizes SQL injection risks.

### 2.3 Authentication & Cryptography
*   **✅ PASS:** `src/auth.py` utilizes the industry-standard `bcrypt` library with generated salts for hashing passwords.
*   **✅ PASS:** JWT tokens are issued with explicit expiration times (`token_expiry_hours`).

## 3. Runtime Risks & Logical Errors

*   **Database Migrations:** `db.py` contains robust `_migrate_legacy_alerts()` logic that transitions older `alerts` table data into the new `alerts_v2` schema.
*   **Path Resolution:** As patched in a previous phase, `os.PathLike` objects are properly converted to string paths before SQLite operations, preventing `TypeError` crashes during initialization.

## 4. Remediation Plan / Recommendations
1.  **Enforce Secrets Override:** Ensure the `install.sh` or deployment documentation explicitly instructs administrators to change the `WATCHMAN_JWT_SECRET` and bootstrap passwords.
2.  **CLI Best Practices:** Refactor `src/cli.py` to prompt the user for a bootstrap password securely (e.g., using `typer.prompt(hide_input=True)`) rather than defaulting to `watchman2026`.

## 5. Conclusion
The codebase is fundamentally secure and free of critical logical or injection flaws. The primary area for improvement revolves around removing default static credentials and enforcing secure configuration during deployment.
