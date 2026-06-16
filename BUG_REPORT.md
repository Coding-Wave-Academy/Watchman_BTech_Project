# BUG REPORT & RISK ASSESSMENT

## 1. Overview
This document outlines the bugs, architectural flaws, and security risks identified during the Phase 3 audit of the WatchMan NIDS repository.

---

## 2. Critical Issues (High Priority)

### 2.1 Predict & Capture Thread Blocking (`src/predict.py`)
*   **Location:** `start_live_capture` -> `process_packet`
*   **Description:** The packet processing logic (feature extraction, `rf.predict`, `iso.decision_function`) is executed *synchronously* inside the `sniff` `prn` callback.
*   **Impact:** Machine learning inference is computationally expensive. Running it in the same thread as packet capture will inevitably cause Scapy to drop packets under high network throughput, leading to missed detections.
*   **Recommendation:** Decouple capture and inference. `process_packet` should only aggregate flows. When a flow is complete, it should be placed in a thread-safe `Queue`. A separate worker pool/thread should pop flows from the queue and perform ML inference.

### 2.2 Potential OOM in Flow Tracker (`src/predict.py`)
*   **Location:** `FlowTracker` class
*   **Description:** `FlowTracker` maintains a dictionary of active flows. Stale flows are only flushed periodically (`if packets_total % 100 == 0`).
*   **Impact:** During a volumetric DDoS attack (e.g., SYN flood), the unique 5-tuple keys will grow exponentially. If the attacker sends fewer than 100 packets per burst or the memory limit is reached before the flush interval efficiently clears idle connections, the system will suffer from Memory Exhaustion (OOM).
*   **Recommendation:** Implement a hard cap on the maximum number of tracked flows (e.g., LRU cache eviction) and use a background timer thread to prune stale flows independent of packet arrival rates.

### 2.3 Privilege Escalation / Failure in IPS (`src/ips.py`)
*   **Location:** `_iptables_block`
*   **Description:** The application invokes `subprocess.run(["iptables", "-A", ...])` directly.
*   **Impact:** `iptables` requires `root` privileges. If the WatchMan backend (FastAPI) is run as a standard user, the subprocess will fail. If the entire FastAPI app is run as `root` to allow `iptables` access, it violates the principle of least privilege, exposing the system if the REST API is compromised.
*   **Recommendation:** The IPS module should ideally communicate with a localized root-owned agent (e.g., via a Unix socket or specific `sudoers` rule for the iptables binary) rather than running the entire NIDS as root.

---

## 3. Moderate Issues (Medium Priority)

### 3.1 Fragile Python Environment Resolution (`electron/main.js`)
*   **Location:** `findPython` function
*   **Description:** The Electron app attempts to locate the Python executable by checking for `.venv/Scripts/python.exe` or `venv/Scripts/python.exe`. If neither exists, it falls back to the system `python` command.
*   **Impact:** If the user has multiple Python versions or lacks global dependencies, the Flask backend will fail to start. The UI might hang indefinitely waiting for the port to bind.
*   **Recommendation:** Package a portable Python environment (e.g., PyInstaller standalone executable for the backend) for production distribution instead of relying on local virtual environments.

### 3.2 Hardcoded Blockchain Credentials (`src/ganache_manager.py`)
*   **Location:** Ganache CLI spawn command
*   **Description:** The mnemonic used to spawn the Ganache instance is hardcoded (`"candy maple cake sugar pudding cream honey rich smooth crumble sweet treat"`).
*   **Impact:** This is acceptable for a local academic demo but presents a severe security risk if the application logic is ever migrated to a public testnet or mainnet without removing this hardcoding.
*   **Recommendation:** Move all blockchain credentials, RPC endpoints, and mnemonics to `.env` or `watchman.config.json` and ensure they are excluded from source control.

### 3.3 Naive Merkle Tree Hashing (`src/merkle.py`)
*   **Location:** `hash_pair`
*   **Description:** The Merkle tree concatenates the left and right hashes directly (`hashlib.sha256(left.encode() + right.encode())`).
*   **Impact:** Without domain separation (e.g., prefixing leaf nodes with `0x00` and internal nodes with `0x01`), it is theoretically vulnerable to a second-preimage attack where an internal node hash is presented as a leaf node.
*   **Recommendation:** Implement standard domain separation prefixes before hashing node pairs.

---

## 4. Summary
The identified bugs primarily relate to **scalability under load** (synchronous capture/prediction) and **deployment robustness** (Electron python path, IPS root privileges). Fixing the synchronous capture loop is the most critical item before exposing the system to a real-world network.
