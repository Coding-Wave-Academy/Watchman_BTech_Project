# Deployment Guide

This guide covers deploying WatchMan to different environments.

## Local Installation (Ubuntu Server / VM)
If deploying locally inside a VM or a bare-metal Ubuntu server:
1. Ensure your network interfaces are set to promiscuous mode if you want to capture network-wide traffic, or just span port traffic.
2. Run `sudo ./install.sh`.
3. Use `watchman configure` to set the correct packet capture interface (e.g., `eth0` or `ens33`).
4. Restart the service: `sudo systemctl restart watchman`.

## VPS Installation (DigitalOcean / AWS / Linode)
When deploying WatchMan to a public VPS to monitor the VPS's own ingress/egress traffic:
1. Create an Ubuntu Droplet/Instance.
2. SSH into the instance: `ssh root@<IP_ADDRESS>`.
3. Clone the repo and run `sudo ./install.sh`.
4. Run `watchman configure` and set the `capture.interface` to your public network interface (usually `eth0`).
5. Expose port `5000` via your firewall (e.g., `ufw allow 5000`) so you can access the dashboard. 

## Cloud Deployment Notes
- **Bandwidth Limits:** Packet capturing can consume CPU. WatchMan's Machine Learning models are optimized, but very high bandwidth nodes (1Gbps+) might see dropped packets.
- **Blockchain Demo Mode:** By default, WatchMan runs in demo mode. To anchor to the Polygon network, update `/etc/watchman/watchman.config.json` with your RPC URL and smart contract address.
