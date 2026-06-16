# CLI Audit Report

## Existing Commands
- `install`: Initializes DB and creates admin user.
- `start`: Starts the FastAPI server in the foreground.
- `config`: Shows current configuration.
- `stop`: Sends API request to stop packet capture.
- `status`: Displays daemon and blockchain health.
- `monitor`: Streams recent alerts to the terminal.
- `alerts`: Lists alerts with filters.
- `verify`: Verifies Merkle proofs.
- `anchor`: Runs anchor cycle.

## Missing Commands
- `configure` (will rename `config` to `configure` and allow interactive editing or file opening).
- `restart` (needs to restart the daemon, usually via systemd).
- `update` (stub for updating the software).
- `uninstall` (stub for uninstalling or deferring to package manager/uninstall.sh).

## Inconsistent Behavior
- `start`: Runs in the foreground, but as a systemd service, it might conflict. The command should detect if systemd is managing it or just wrap `systemctl start watchman` if installed.
- `stop`: Stops the packet capture via API, but users expect `stop` to stop the entire daemon/service in a CLI-first product.
- Path handling is heavily tied to `watchman_config.py` which needs to be refactored to standard Linux paths (`/etc/watchman`, etc.) so CLI points to those properly.

## Action Plan
1. Rename `config` to `configure`.
2. Update `start`/`stop`/`restart` to interact with `systemctl` if running on Linux with systemd, or fallback to API/foreground methods.
3. Add `update` to execute `git pull` and `pip install -r requirements.txt`.
4. Add `uninstall` to instruct the user to run `uninstall.sh`.
