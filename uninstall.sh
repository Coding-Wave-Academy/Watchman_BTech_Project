#!/usr/bin/env bash
set -e

echo "=========================================="
echo " WatchMan NIDS - Uninstallation Script"
echo "=========================================="

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (e.g. sudo ./uninstall.sh)"
  exit 1
fi

echo "[1/4] Stopping Service..."
systemctl stop watchman.service || true
systemctl disable watchman.service || true
rm -f /etc/systemd/system/watchman.service
systemctl daemon-reload

echo "[2/4] Removing Files..."
rm -rf /opt/watchman
rm -rf /etc/watchman
rm -rf /var/log/watchman
rm -rf /var/lib/watchman
rm -rf /tmp/watchman

echo "[3/4] Removing User..."
if id "watchman" &>/dev/null; then
    userdel watchman || true
fi

echo "[4/4] Removing CLI symlink..."
if [ -f /usr/local/bin/watchman ]; then
    rm /usr/local/bin/watchman
fi

echo "=========================================="
echo " Uninstallation Complete."
echo "=========================================="
