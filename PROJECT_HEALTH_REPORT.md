# WatchMan NIDS - Project Health Report

**Date:** 2026-06-15
**Phase:** 1 - Full Repository Analysis

## 1. Project Overview
WatchMan is a Network Intrusion Detection System (NIDS) designed for robust network security, combining Machine Learning (ML) for anomaly detection with Blockchain technology (Polygon/Ganache) for immutable alert logging and integrity verification. The project is intended for professional deployment as a B.Tech project.

## 2. Architecture
The project follows a modular, microservice-inspired architecture:
*   **Backend API (FastAPI):** Serves the dashboard and handles configurations/alert retrieval.
*   **Detection Daemon (`detection_service.py`):** Runs continuously in the background, capturing packets and predicting threats using the ML pipeline.
*   **IPS Engine (`ips.py`):** Interacts with OS-level firewalls (e.g., `iptables`) to block malicious IPs.
*   **Blockchain Integration (`blockchain.py`):** Anchors alerts into a local Ganache instance or Polygon network using Web3.py.
*   **Frontend Dashboard (`dashboard/`):** A React/Vite Single Page Application (SPA) providing visualization, configuration management, and alert tracking.
*   **CLI (`cli.py`):** A command-line interface for system administration, service management, and diagnostics.

## 3. Folder Structure
```text
Watchman_BTech_Project/
├── src/                # Core Python backend
│   ├── app.py          # FastAPI application
│   ├── cli.py          # Typer CLI application
│   ├── db.py           # SQLite database logic
│   ├── detection_service.py # Packet capture & ML inference daemon
│   ├── ips.py          # Intrusion Prevention System
│   ├── blockchain.py   # Web3 interactions
│   └── ...             # ML pipeline & configuration
├── dashboard/          # React + Vite frontend
├── tests/              # Pytest suite
├── models/             # Serialized ML models (.pkl)
├── data/               # PCAP datasets and logs
├── docs/               # Documentation
└── install.sh          # Deployment script
```

## 4. Dependencies
**Python (Backend):**
*   **Core API & CLI:** `fastapi`, `uvicorn`, `pydantic`, `typer`, `rich`
*   **Machine Learning:** `scikit-learn`, `numpy`, `pandas`, `joblib`
*   **Networking:** `scapy`, `requests`, `httpx`
*   **Blockchain:** `web3`
*   **Testing:** `pytest`

**Node.js (Frontend):**
*   **Framework:** React, Vite, TypeScript
*   **Styling:** TailwindCSS, Shadcn UI

## 5. Component Deep Dive

### 5.1 Machine Learning Pipeline
Located in `src/predict.py`, `src/preprocessing.py`, `src/train.py`, and `src/cross_validate.py`. The system uses standard Scikit-Learn workflows (likely Random Forest or similar) to classify network traffic based on extracted features. Models are persisted using `joblib`.

### 5.2 Packet Capture Component
Integrated within `src/detection_service.py` and potentially leveraging `scapy` for raw packet ingestion and feature extraction before handing data over to the ML model.

### 5.3 Database
Managed by `src/db.py` using SQLite. Contains crucial tables like `alerts_v2` for storing threat events and `blocked_ips` for maintaining state across the IPS engine.

### 5.4 Blockchain Component
`src/blockchain.py` and `src/ganache_manager.py` handle connection and interaction with an Ethereum-compatible node (Ganache for testing, Polygon for production). Alerts are hashed (potentially via `merkle.py`) and anchored to the blockchain (`anchoring.py`) to ensure they cannot be tampered with.

### 5.5 Intrusion Prevention System (IPS)
`src/ips.py` reads from the ML predictions and inserts blocking rules via `iptables`. It works in tandem with `db.py` and `app.py` to allow manual unblocking/blocking through the dashboard.

## 6. Current Health Status
*   **Database Integration:** Fixed path handling and schema (`blocked_ips`) in recent updates.
*   **IPS Integration:** Resolved variable scope and schema mismatch (`alerts` vs `alerts_v2`).
*   **Configuration:** Migration logic fixed to prevent silent overwrites.
*   **Testing:** The pytest suite and frontend build process pass successfully.

**Conclusion:** The project foundation is solid and operational. The core components (ML, Blockchain, API, IPS) are wired correctly. The repository is ready to proceed to static analysis, build verification, and deployment readiness checks.
