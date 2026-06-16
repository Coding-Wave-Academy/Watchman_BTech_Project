# Systemd Service Documentation

WatchMan NIDS is managed via `systemd` on Linux, ensuring it starts on boot, restarts on crash, and logs output properly.

## Service Commands

### Status Check
Check if the daemon is running and view recent logs:
```bash
sudo systemctl status watchman
```

### Start/Stop/Restart
Manually control the service state:
```bash
sudo systemctl start watchman
sudo systemctl stop watchman
sudo systemctl restart watchman
```

### Auto-start
Enable or disable auto-starting the daemon when the server boots:
```bash
sudo systemctl enable watchman
sudo systemctl disable watchman
```

## Viewing Logs via Journalctl

Since WatchMan is integrated with systemd, its stdout and stderr logs are also captured by the `systemd-journald` service in addition to the static files in `/var/log/watchman/`.

To view a live feed of the logs:
```bash
sudo journalctl -u watchman -f
```

To view the last 100 lines:
```bash
sudo journalctl -u watchman -n 100
```

## Service File Location
The unit file is installed at `/etc/systemd/system/watchman.service`.

### Security Note
The service runs as a dedicated `watchman` non-root user for security. However, to allow packet capturing via `scapy`, the service is granted `CAP_NET_RAW` and `CAP_NET_ADMIN` capabilities via the `AmbientCapabilities` directive in the unit file.
