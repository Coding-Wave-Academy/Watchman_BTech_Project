# WatchMan Architecture

WatchMan is a monolithic application with modular internal subsystems. It acts as both the sensor (Packet Capture) and the manager (Dashboard/API) on the same machine.

## Components

### 1. The Sensor (Packet Capture)
Located in `src/detection_service.py` and `src/runner.py`.
It uses `scapy` to sniff raw packets from your network interface (e.g., `eth0`). It groups packets into bidirectional flows.

### 2. The Brain (Machine Learning Engine)
Located in `src/predict.py` and `src/preprocessing.py`.
Once a flow ends or reaches a timeout, the flow statistics are extracted and passed to a Scikit-Learn `RandomForestClassifier`. The model determines the probability that the flow is malicious (e.g., DoS, Port Scan).

### 3. The Enforcer (Intrusion Prevention System - IPS)
Located in `src/ips.py`.
If the ML engine detects an attack with high confidence, the IPS module dynamically generates an `iptables` rule to drop all future traffic from the attacker's IP address.

### 4. The Auditor (Blockchain Module)
Located in `src/anchoring.py` and `src/merkle.py`.
Periodically, the system takes all new alerts, generates a Merkle Root Hash of their contents, and sends a transaction to a Smart Contract on the Polygon blockchain (or Ganache locally). This ensures logs cannot be silently deleted by an attacker who compromises the server.

### 5. The Interface (FastAPI & Dashboard)
Located in `src/app.py` and `dashboard/`.
The FastAPI backend serves the REST API and hosts the React Dashboard. The dashboard communicates with the backend to display data in a user-friendly way.
