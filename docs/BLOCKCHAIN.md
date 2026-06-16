# Blockchain Integration

WatchMan uses blockchain technology not for cryptocurrencies, but for **Immutable Forensic Auditing**.

## The Problem
If a highly skilled attacker breaches your server, the first thing they do is delete the system logs and NIDS alerts to cover their tracks. Without logs, you cannot conduct a post-incident forensic investigation.

## The WatchMan Solution
WatchMan prevents log tampering using cryptographic Anchoring.

1. **Batching:** When alerts occur, they are stored in the local SQLite database.
2. **Hashing:** Every 15 minutes, the `anchoring.py` service gathers all new alerts and hashes them using SHA-256.
3. **Merkle Tree:** These hashes are combined into a Merkle Tree. A single "Root Hash" is generated that represents the entire batch of alerts.
4. **Smart Contract:** The Root Hash is sent as a transaction to the `NIDSLogger` Smart Contract.

## Verification
If an auditor wants to prove an alert is genuine and hasn't been altered:
1. They select the alert in the Dashboard.
2. WatchMan recalculates the hash of the alert data.
3. It fetches the Merkle Proof and the Root Hash from the Blockchain.
4. If the calculated hash matches the path in the immutable Root Hash, the alert is mathematically proven to be authentic.

## Supported Networks
* **Ganache:** Local testing network (Demo Mode - default).
* **Polygon PoS:** Production network (Requires configuring an RPC URL and a private key with MATIC tokens in `watchman_config.json`).
