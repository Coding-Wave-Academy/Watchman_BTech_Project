# Troubleshooting Guide

If you encounter issues while running WatchMan, follow these steps to diagnose and resolve the problem.

## 1. The WatchMan Service Fails to Start

**Symptom:** Running `watchman start` does not bring the dashboard online, or `watchman status` shows it as failed.

**Diagnostic:**
Check the system logs:
```bash
sudo journalctl -u watchman -n 50 --no-pager
```
Or check the application logs:
```bash
cat logs/watchman.log
```

**Common Causes:**
* **Port Conflict:** Port 8000 is already in use by another application. Edit `watchman_config.json` to change the `api.port`.
* **Missing Dependencies:** Ensure `install.sh` completed without errors. Try running `pip install -r requirements.txt` again.

## 2. No Alerts are Being Generated

**Symptom:** You are running WatchMan, but the dashboard shows 0 active alerts after a long time.

**Diagnostic:**
WatchMan might be sniffing the wrong network interface. By default, it listens on all interfaces (`any`) or `eth0`.
Check the logs for `PermissionError` when starting Scapy.

**Solution:**
Ensure WatchMan is running with the necessary network capabilities. Run `sudo setcap cap_net_raw,cap_net_admin=eip src/runner.py` or use the systemd service.

## 3. IPS is not Blocking Attackers

**Symptom:** Alerts show as "Blocked" in the dashboard, but the attacker is still able to connect.

**Diagnostic:**
Check if the iptables rule was actually added:
```bash
sudo iptables -L -n | grep DROP
```

**Solution:**
If using a conflicting firewall manager like UFW, it might flush WatchMan's rules. Ensure WatchMan is allowed to insert raw `iptables` rules, or manually integrate the banned IPs into your primary firewall tool.

## 4. Blockchain Anchoring Fails

**Symptom:** The dashboard shows "Last Error" under the Blockchain status.

**Solution:**
If in Demo Mode, ensure Ganache is installed (`npm install -g ganache`) and running.
If in Production Mode, check that your `rpc_url` in the config is valid and that your wallet has enough MATIC to pay gas fees.
