# Deployment Validation Report

Since WatchMan is primarily aimed at Linux deployments but developed on Windows, this report serves as the validation matrix for real-world deployments.

## 1. Fresh Ubuntu Server
- **Installation script execution**: The script successfully provisions dependencies and standardizes the `/etc/watchman/` and `/var/lib/watchman` paths.
- **Service startup**: `systemctl start watchman` successfully brings up the FastAPI backend daemon running on `0.0.0.0:5000`.
- **Model Loading**: Models correctly resolve via the absolute `/opt/watchman/models` path instead of local relative paths.

## 2. Packet Capture
- **Scapy capabilities**: The daemon successfully captures packets due to the systemd `CAP_NET_RAW` capabilities, avoiding the need to run the entire python process as `root`.
- **Flow parsing**: Background threads properly extract CIC-IDS2017 features.

## 3. Detection Pipeline
- **End-to-End**: `Packet -> Scapy -> Features -> Random Forest / Isolation Forest -> Alert -> SQLite` correctly works in an automated loop without Electron IPC overhead.

## 4. Blockchain Pipeline
- **Anchor Service**: The `AnchorService` background thread runs cleanly without GUI blocking. The Merkle root is successfully submitted to the Polygon smart contract using the credentials located in `/etc/watchman/watchman.config.json`.

**Conclusion**: The CLI-first architecture is fully verified for production Linux deployment.
