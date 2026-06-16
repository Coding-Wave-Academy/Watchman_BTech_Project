# How to Use WatchMan NIDS

This document outlines how to interact with the WatchMan NIDS through its various interfaces: the Electron Dashboard, the Command-Line Interface (CLI), and the REST API.

## 1. Electron Dashboard

The WatchMan NIDS dashboard is the primary user interface. 

### Key Features:
- **Overview**: Displays system status (API and Blockchain daemon), current packet capture status, and high-level statistics.
- **Alerts Feed**: Shows a real-time stream of network intrusions and anomalies detected by the ML models.
- **Alert Management**: Click on any alert to view its details, including the packet payload, matched ML features, and confidence score. Administrators can update the alert status (e.g., mark as resolved or false positive).
- **System Controls**: Start and stop packet capture directly from the UI.
- **Blockchain Verification**: View the Merkle proof for specific alerts to verify they haven't been tampered with.

## 2. Command-Line Interface (CLI)

The Typer-based CLI provides a powerful way to manage the NIDS without a graphical interface. All commands are executed via `python src/cli.py`.

### Available Commands:

- **`install`**: Initializes the database (`alerts.db`) and creates the default admin user (`admin` / `watchman2026`).
- **`start`**: Starts the FastAPI backend server on port 5000.
- **`stop`**: Stops the active network packet capture process.
- **`status`**: Displays the current health and status of the system, including capture status and blockchain daemon connection.
- **`monitor`**: Opens a live stream of network alerts directly in the terminal via WebSockets.
- **`alerts`**: Lists recent alerts. Supports filtering (e.g., by attack type or time window).
- **`verify`**: Verifies the blockchain proof for a specific alert ID.
- **`anchor`**: Manually triggers one Merkle tree anchor cycle to the blockchain.

**Example Usage:**
```bash
python src/cli.py status
python src/cli.py alerts --limit 10 --attack-type "DDoS"
```

## 3. API Reference

The backend exposes a REST API powered by FastAPI. Authentication requires a JWT token passed in the `Authorization` header (`Bearer <token>`).

### Public Endpoints
- **`POST /auth/login`**: Authenticate and retrieve a JWT token.
- **`GET /health`**: System health check.

### Protected Endpoints (Requires JWT)
- **`GET /alerts`**: List alerts. 
  - *Query Params*: `limit` (int), `attack_type` (str), `hours` (int).
- **`GET /alerts/stats`**: Retrieve aggregate statistics for the dashboard.
- **`GET /alerts/{id}`**: Get detailed information for a single alert.
- **`PUT /alerts/{id}/status`**: Update the status of an alert (Admin only).
- **`GET /system/status`**: Get NIDS daemon and blockchain connection status.
- **`POST /system/start`**: Start network packet capture (Admin only).
- **`POST /system/stop`**: Stop network packet capture (Admin only).
- **`POST /system/anchor`**: Manually run a blockchain anchor cycle (Admin only).
- **`GET /verify/{id}`**: Verify an alert's Merkle proof against the blockchain.

### WebSocket
- **`WS /ws/alerts?token=...`**: Connect to receive a real-time stream of newly generated alerts.
