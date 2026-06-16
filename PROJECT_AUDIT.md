# PROJECT AUDIT: WatchMan NIDS

## 1. Executive Summary
WatchMan is a comprehensive Network Intrusion Detection System (NIDS) designed as a Bachelor of Technology final-year project. It bridges Machine Learning (for detecting known and zero-day threats) with Blockchain technology (for providing an immutable, cryptographically verifiable audit log of intrusions). The project is a hybrid application featuring a Python/FastAPI backend, an Electron-based frontend desktop application, and a local Ethereum (Ganache) blockchain node.

**Current Status:** The core architecture is fully implemented, including ML training pipelines, live packet capture, REST/WebSocket APIs, IPS capabilities, and smart contract anchoring. However, several areas require stabilization before production deployment, particularly regarding platform-specific dependencies (e.g., `iptables` for IPS) and process lifecycle management (Electron spawning Flask and Ganache).

---

## 2. Architecture & Components

### 2.1 Backend / Core Logic (Python)
The backend is built around **FastAPI** (`src/app.py`) and serves as the orchestrator for the following modules:
*   **Packet Capture & ML Detection (`src/predict.py`, `src/detection_service.py`):** Uses Scapy to sniff traffic on a specified interface. Extracts 78 flow features and passes them through a pre-trained Random Forest (for known attacks) and an Isolation Forest (for anomalies/zero-days).
*   **Intrusion Prevention System (`src/ips.py`):** Modifies host `iptables` rules to block malicious IPs. Supports `enforce` (requires root on Linux) and `simulate` (fallback for Windows/demo) modes.
*   **Database (`src/db.py`):** SQLite persistence layer storing users, system state, and detected alerts. Includes migration logic from legacy schemas.
*   **Blockchain Anchoring (`src/merkle.py`, `src/anchoring.py`, `src/blockchain.py`):** Alerts are batched, structured into a Merkle tree, and the root is anchored to an Ethereum smart contract (`NIDSLogger`).
*   **Ganache Manager (`src/ganache_manager.py`):** Automatically spawns a Ganache CLI subprocess using a deterministic mnemonic and deploys the smart contract if not found.
*   **CLI (`src/cli.py`):** A Typer-based command-line interface for administration, installation, and monitoring without the GUI.

### 2.2 Frontend (Electron & Web)
*   **Electron Main Process (`electron/main.js`):** Manages the application lifecycle. Crucially, it manages the Python Flask subprocess and checks for system readiness (port binding).
*   **Onboarding (`electron/onboarding.html`):** A setup wizard that validates system requirements (Python, Flask, Models, Ganache) and configures the monitoring interface.
*   **Dashboard (`dashboard/index.html`):** The primary UI served by FastAPI, displaying real-time alerts via WebSockets, system health, and blockchain verification tools.
*   **Landing Page (`landing.html`):** A marketing/demonstration page outlining features and pricing tiers.

### 2.3 Machine Learning Pipeline
*   **Preprocessing (`src/preprocessing.py`):** Cleans the CICIDS2017 dataset, handling infinities, missing values, and mapping labels to 5 core categories (Normal, DoS, BruteForce, PortScan, Anomaly).
*   **Training (`src/train.py`):** Applies SMOTE to the training set only (preventing data leakage), trains the Random Forest and Isolation Forest models, and exports them via Joblib.
*   **Cross Validation (`src/cross_validate.py`):** Validates the *methodology* against NSL-KDD and UNSW-NB15 datasets.

### 2.4 Blockchain & Smart Contracts
*   **Contract (`blockchain/contracts/nidslogger.sol`):** A Solidity contract that stores alert IDs, IPs, ports, types, confidence, and a keccak256 hash.
*   **Truffle Config (`blockchain/truffle-config.js`):** Configuration for deploying the contract to the local Ganache network (port 7545).

---

## 3. Initial Bug & Risk Assessment (High-Level)

1.  **Process Management Fragility (Electron/Flask/Ganache):**
    *   `electron/main.js` relies on heuristics to find the Python executable (e.g., checking `.venv` and `venv`). If it falls back to the system Python, dependencies may be missing.
    *   Ganache is spawned via `ganache_manager.py` and Flask via `main.js`. Zombie processes can occur if the Electron app crashes before cleaning up subprocesses.
2.  **IPS Compatibility & Permissions:**
    *   `src/ips.py` strictly relies on Linux `iptables`. On Windows or macOS, it correctly defaults to `simulate` mode, but users expecting actual prevention on those platforms will be confused. Even on Linux, the daemon requires `sudo` privileges to execute `iptables` commands, which conflicts with running the FastAPI app securely.
3.  **Scapy Performance Bottleneck:**
    *   Live packet capture using Scapy in Python (`src/predict.py`) is notoriously slow under heavy traffic loads. The flow aggregation dictionary (`active_flows`) may consume excessive memory if flow timeouts are not aggressively managed during a DDoS attack.
4.  **Blockchain Hardcoding:**
    *   Ganache is hardcoded to use a specific deterministic mnemonic. While suitable for a demo/BTech project, transitioning to a live testnet/mainnet (like Polygon, as mentioned in the project goals) requires extracting keys and endpoints into environment variables.
5.  **Authentication & Security:**
    *   JWT secret is sourced from configuration (`jwt_secret`), but it is unclear if this is securely randomly generated on installation or hardcoded.

## 4. Next Steps
The project structure is sound and well-documented for an academic project. The next phases will involve:
*   Generating the Requirement Compliance Report (`SCOPE_COMPLIANCE_REPORT.md`).
*   Deep-diving into specific bugs (`BUG_REPORT.md`).
*   Reviewing code quality and deployment readiness.
