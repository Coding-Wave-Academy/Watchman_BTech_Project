# WatchMan Installation Guide

WatchMan is designed to be installed on a fresh Ubuntu Server (20.04 or 22.04).

## System Requirements
- Ubuntu Server 20.04 or 22.04
- 2GB+ RAM
- Python 3.8+
- Root (sudo) access

## Automated Installation

The easiest way to install WatchMan is via the automated installation script.

```bash
git clone https://github.com/WatchMan/watchman-nids.git
cd watchman-nids
sudo ./install.sh
```

### What `install.sh` Does:
1. Installs Python dependencies (`python3-venv`, `python3-pip`).
2. Creates standardized directories (`/etc/watchman`, `/var/log/watchman`, `/var/lib/watchman`).
3. Creates a dedicated, non-root `watchman` user.
4. Copies the project to `/opt/watchman/app` and creates a virtual environment.
5. Installs WatchMan globally as a CLI tool.
6. Initializes the database and creates the default admin user.
7. Installs and starts the `watchman` systemd service.

## Post-Installation

Once installed, the CLI tool `watchman` is available globally.

Verify the installation:
```bash
watchman status
```

Start monitoring:
```bash
watchman start
```
