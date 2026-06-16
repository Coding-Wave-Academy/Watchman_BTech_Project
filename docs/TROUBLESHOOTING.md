# Troubleshooting

## CLI Command Not Found
**Error:** `watchman: command not found`
**Fix:** Ensure `/usr/local/bin` is in your PATH, or run the command directly via `/opt/watchman/app/.venv/bin/watchman`. You can also re-run `sudo ./install.sh`.

## Packet Capture Permission Denied
**Error:** `scapy` throws an `Operation not permitted` error.
**Fix:** Ensure the `watchman` systemd service has `AmbientCapabilities=CAP_NET_RAW CAP_NET_ADMIN` in `/etc/systemd/system/watchman.service`. Run `sudo systemctl daemon-reload` and `sudo systemctl restart watchman`.

## Database Locked
**Error:** `sqlite3.OperationalError: database is locked`
**Fix:** Ensure no other process (like an old detached foreground process) is holding the database open. Run `sudo systemctl restart watchman`.

## Daemon Crashing on Boot
**Error:** `systemctl status watchman` shows it as failed.
**Fix:** Check the logs: `sudo journalctl -u watchman -f`. It might be due to a missing Python dependency or an invalid `/etc/watchman/watchman.config.json`.
