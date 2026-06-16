# SCOPE COMPLIANCE REPORT

## 1. Overview
This report evaluates the WatchMan NIDS implementation against its stated core objectives to determine the current level of project completeness and adherence to the initial requirements.

## 2. Objectives Evaluation

| Objective | Status | Implementation Details | Notes |
| :--- | :---: | :--- | :--- |
| **1. Capture network traffic in real time.** | ✅ Fully Met | Utilizes `scapy.sniff` in `src/predict.py` to capture live packets on the specified interface. | The implementation runs in a background thread managed by `detection_service.py`. |
| **2. Extract network flow features.** | ✅ Fully Met | Manual feature extraction logic in `src/predict.py` aggregates packets into bidirectional flows, matching 78 statistical features used by the CICIDS2017 dataset. | Flow timeouts are handled, though performance under high traffic loads requires stress testing. |
| **3. Detect attacks using machine learning.** | ✅ Fully Met | Random Forest model trained on CICIDS2017 to classify DoS, PortScan, and BruteForce attacks. | Achieves reported high accuracy (99.88% in training). |
| **4. Detect unknown traffic using anomaly detection.** | ✅ Fully Met | Isolation Forest model trained exclusively on normal traffic to detect zero-day anomalies. | Runs as a secondary layer alongside the Random Forest. |
| **5. Generate alerts.** | ✅ Fully Met | Detection loop yields structured alert dictionaries upon positive classification. | Thresholds are configurable via `watchman.config.json`. |
| **6. Store alerts locally.** | ✅ Fully Met | SQLite database (`src/db.py`) securely persists alerts in the `alerts_v2` table. | |
| **7. Build Merkle trees from alerts.** | ✅ Fully Met | `src/merkle.py` constructs a valid Merkle tree from batches of unanchored alerts. | |
| **8. Anchor Merkle roots on Polygon blockchain.** | ⚠️ Partially Met | Currently anchors to a local **Ganache** Ethereum node (`src/ganache_manager.py`). | Requires configuration updates (RPC endpoint, private key management) to transition from Ganache to the live Polygon mainnet/testnet. |
| **9. Provide cryptographic verification of alerts.** | ✅ Fully Met | Endpoint `/verify/{id}` (`src/app.py`) fetches the alert, reconstructs the hash, and verifies it against the blockchain record. | |
| **10. Expose REST APIs.** | ✅ Fully Met | FastAPI application provides robust endpoints (`/alerts`, `/verify`, `/system/status`, `/auth/login`). | Fully functional and powers the frontend dashboard. |
| **11. Provide CLI management tools.** | ✅ Fully Met | `src/cli.py` uses Typer to provide commands like `install`, `start`, `status`, `monitor`, and `alerts`. | |
| **12. Provide a lightweight web dashboard.** | ✅ Fully Met | HTML/JS dashboard (`dashboard/index.html`) communicating via REST and WebSockets. Wrapped in Electron for desktop delivery. | |
| **13. Support optional intrusion prevention (firewall).** | ✅ Fully Met | `src/ips.py` interfaces with `iptables` to block malicious IP addresses. | Supports `enforce` (Linux only, requires root) and `simulate` (cross-platform safe mode). |

## 3. Conclusion
WatchMan demonstrates a **highly successful** implementation of its stated goals. 12 out of 13 core objectives are fully met. The only partial completion is Objective 8 (Polygon anchoring), which is currently executing successfully on a local Ganache environment but requires parameterization to point to the live Polygon network.

The project is feature-complete for an academic/BTech demonstration and requires only stabilization and environment configuration for a production-like deployment.
