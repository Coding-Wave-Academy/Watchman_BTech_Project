# Frequently Asked Questions (FAQ)

### What is the difference between WatchMan and Snort/Suricata?
Snort and Suricata are primarily **signature-based** systems. They rely on rules written by humans. If an attacker uses a zero-day exploit that doesn't have a rule, those systems might miss it. WatchMan is **Machine Learning-based**. It learns the statistical patterns of normal and abnormal traffic, allowing it to detect novel, unseen attacks based on behavior.

### Does WatchMan slow down my internet connection?
No. WatchMan passively sniffs network traffic. It does not act as an inline proxy (unless IPS is triggered to drop packets). It will not slow down your network throughput.

### What happens if I lose my Blockchain Private Key?
If you lose the private key in `watchman_config.json`, you will no longer be able to anchor new alerts to the same contract address. However, past alerts remain mathematically verifiable on the blockchain forever.

### How much does it cost to use the Blockchain feature?
If running in "Demo Mode", it is entirely free. If running on Polygon Mainnet, each anchor transaction costs a fraction of a cent in MATIC. Because WatchMan batches alerts using Merkle Trees, anchoring 1,000 alerts costs the same as anchoring 1 alert.

### I locked myself out of the dashboard!
Use the CLI on the server to reset your password:
```bash
watchman users chpasswd admin new_secure_password
```
