# WatchMan Deployment Guide

This guide explains how to deploy WatchMan in a production-like environment (e.g., a VPS or dedicated server) rather than just a local testing machine.

## Architecture Overview

A production WatchMan deployment consists of:
1. **The Daemon Service:** A `systemd` background process that runs `src/runner.py`.
2. **The API Server:** A FastAPI application running on port 8000.
3. **The Web Dashboard:** A React frontend served by the API server.
4. **The IPS Module:** A subsystem that directly manages `iptables` to block threats.

## 1. System Preparation

Ensure your server is secured before exposing WatchMan to the internet. 

> [!WARNING]
> Do NOT expose the dashboard port (8000) directly to the public internet without changing the default admin password.

```bash
# Update the system
sudo apt update && sudo apt upgrade -y
```

## 2. Managing the Systemd Service

During installation, a `watchman.service` file was created in `/etc/systemd/system/`.

To enable WatchMan to start automatically when the server reboots:

```bash
sudo systemctl enable watchman
```

To view the real-time logs of the deployment:

```bash
sudo journalctl -u watchman -f
```

## 3. Reverse Proxy (Nginx) - Recommended

Instead of accessing port 8000 directly, you should set up Nginx as a reverse proxy with SSL (HTTPS).

Install Nginx:
```bash
sudo apt install nginx -y
```

Create a configuration file (`/etc/nginx/sites-available/watchman`):
```nginx
server {
    listen 80;
    server_name watchman.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # Enable WebSockets for live alerts
    location /ws/ {
        proxy_pass http://127.0.0.1:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Enable the site and restart Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/watchman /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

## 4. Production Security

*   Update your passwords immediately using the CLI.
*   Ensure `iptables` is not being managed by conflicting tools like `ufw` or `firewalld` without proper bridging, as WatchMan's IPS needs to insert block rules.
