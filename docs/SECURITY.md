# WatchMan Security Guidelines

Deploying a security tool requires ensuring the tool itself is secure. WatchMan is designed with defense-in-depth principles.

## 1. Operating System Security

* **Do not run WatchMan as root if avoidable.** While the `ips.py` module requires `CAP_NET_ADMIN` to manage iptables, the `watchman.service` file is configured to drop unnecessary privileges and only retain network capabilities.
* Ensure your server has a restrictive firewall default policy.

## 2. API Security

* **Change the Default Admin Password:** Upon first installation, use the CLI `watchman users chpasswd admin <new_password>` to change the default password.
* **Use HTTPS:** The FastAPI server runs over HTTP by default. In production, always place it behind a reverse proxy (like Nginx) configured with Let's Encrypt SSL certificates. Do not transmit JWT tokens over plain HTTP on the open internet.

## 3. Database Security

* The SQLite database `alerts.db` contains sensitive network logs. Ensure the directory it resides in (`/data`) has strict permissions (e.g., `chmod 700`).

## 4. Blockchain Private Key Security

* If you switch from Demo Mode to Production Mode, you must supply a Polygon Wallet Private Key in `watchman_config.json`.
* **NEVER** commit your `watchman_config.json` to GitHub if it contains a real private key.
* Ensure the config file is only readable by the WatchMan service user (`chmod 600 watchman_config.json`).
