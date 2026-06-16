# WatchMan CLI Reference

The WatchMan Command Line Interface (CLI) is the easiest way to control the NIDS from your server terminal.

When you ran `install.sh`, it created a global `watchman` command.

## Basic Commands

### Start the Service
Starts the WatchMan NIDS daemon and the API server in the background.
```bash
watchman start
```

### Stop the Service
Stops the daemon and the API gracefully.
```bash
watchman stop
```

### Restart the Service
```bash
watchman restart
```

### Check Status
Shows whether the system is running, the number of alerts, and recent IPS blocks.
```bash
watchman status
```

---

## Intrusion Prevention System (IPS) Management

You can manually manage the blocked IPs using the CLI.

### Block an IP Address
Manually adds an IP to the firewall blocklist.
```bash
watchman ips block 192.168.1.100
```

### Unblock an IP Address
Removes an IP from the firewall blocklist.
```bash
watchman ips unblock 192.168.1.100
```

### List Blocked IPs
View all currently blocked IP addresses.
```bash
watchman ips list
```

---

## User Management

Manage API and Dashboard users.

### Create a User
```bash
watchman users create myusername mypassword
```

### Change a Password
```bash
watchman users chpasswd myusername newpassword
```

---

## Blockchain Management

### Force Anchor
Manually trigger a blockchain anchor of all pending (un-anchored) alerts immediately.
```bash
watchman blockchain anchor
```
