# Changelog

## [1.0.1] - 2026-06-15
### Added
- Completed 10-phase Pre-GitHub Stabilization Audit.
- Added comprehensive project health, build, static analysis, feature validation, and deployment readiness reports.
- Root `.gitignore` to sanitize repository for Git publication.

### Fixed
- Fixed database initialisation bugs preventing proper path resolution (`os.PathLike` to string conversion).
- Patched `watchman_config.py` migration script to prevent dictionary overwriting.
- Fixed IPS module schema queries (`alerts` to `alerts_v2`) to accurately block/unblock IPs from the dashboard.
- Remedied `WATCHMAN_IPS_CHAIN` unbound variable errors in `ips.py`.

## [1.0.0] - 2026-06-09
### Removed
- Removed the Electron framework completely (`electron/` directory deleted).
- Removed desktop packaging dependencies (`electron-builder`, `electron-packager`).
- Removed Windows deployment workflow and desktop installers.
- Eliminated Electron IPC loops and GUI-based packet capture controls.

### Added
- CLI-first architecture using the `watchman` command for all operations.
- Native Linux installer script (`install.sh`) and uninstaller (`uninstall.sh`).
- Systemd integration (`watchman.service`) with `CAP_NET_RAW` permissions.
- Python packaging support (`setup.py` and `pyproject.toml`).
- Comprehensive deployment documentation (`INSTALLATION.md`, `DEPLOYMENT.md`, `SYSTEMD.md`, etc.).
- Linux filesystem standardization (`/etc/watchman`, `/var/lib/watchman`, `/var/log/watchman`).

### Fixed
- Hardcoded Windows path logic replaced with dynamic Linux fallback handling.
- Unified background threads to run smoothly inside a headless FastAPI daemon.
