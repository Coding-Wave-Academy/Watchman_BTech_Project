# WatchMan NIDS

WatchMan NIDS is a Network Intrusion Detection System built with Python, Electron, Machine Learning, and Blockchain technology. It is developed as a B.Tech final-year project to provide secure, immutable, and intelligent network monitoring.

## Features

- **Machine Learning Detection**: Uses Random Forest (supervised learning) and Isolation Forest (anomaly detection) trained on the CIC-IDS2017 dataset to classify and detect network intrusions.
- **Blockchain Anchoring**: Implements a Merkle tree batching mechanism to anchor alert hashes to a blockchain (demo mode by default, optional Polygon deployment), ensuring the immutability of security logs.
- **Real-time Monitoring**: Provides a real-time stream of network alerts using WebSockets.
- **Desktop Application**: A cross-platform Electron frontend wrapping a comprehensive web dashboard.
- **Robust Backend**: Powered by FastAPI and Uvicorn.
- **Command-Line Interface (CLI)**: A powerful Typer-based CLI for administration and monitoring.

## Architecture Overview

The system consists of several integrated components:

1. **Packet Capture & Analysis**: Monitors network interfaces using Scapy and extracts features.
2. **Machine Learning Engine**: Evaluates extracted features against pre-trained Random Forest and Isolation Forest models.
3. **Backend Server**: A FastAPI application that serves API endpoints, manages the SQLite database (`alerts.db`), handles JWT authentication, and pushes real-time alerts via WebSockets.
4. **Blockchain Module**: Aggregates alerts into a Merkle tree. The root hash is periodically anchored to a smart contract (`NIDSLogger.sol`) to provide verifiable integrity.
5. **Frontend / Electron App**: Consumes the backend APIs to present a user-friendly dashboard for managing alerts and system status.
6. **CLI Tool**: `cli.py` provides administrative commands directly from the terminal.

## Quick Links

- [Getting Started Guide](docs/GETTING_STARTED.md)
- [How to Use (Dashboard, API, CLI)](docs/HOW_TO_USE.md)
- [Blockchain Setup Guide](docs/BLOCKCHAIN_SETUP.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

## Tech Stack

- **Backend**: Python, FastAPI, SQLite, JWT
- **Frontend**: Electron, Node.js, WebSockets
- **Machine Learning**: Scikit-Learn, Pandas, NumPy
- **Blockchain**: Solidity, Truffle, Web3.py

## License
[Add License Here]
