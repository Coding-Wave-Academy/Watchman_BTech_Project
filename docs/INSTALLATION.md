# WatchMan Installation Guide

Welcome to the WatchMan NIDS! This guide is written for complete beginners. If you've never used a Network Intrusion Detection System before, don't worry—we've automated the hard parts.

## Prerequisites

Before you begin, ensure you have:
* A machine running **Ubuntu 22.04 LTS** (or newer).
* **Root/Sudo privileges** (WatchMan needs to interact with the firewall to block attacks).
* Python 3.10+ installed.
* At least 2GB of RAM and 2 CPU cores.

## Step 1: Download the Project

First, download the WatchMan source code from our GitHub repository using `git`:

```bash
git clone https://github.com/Coding-Wave-Academy/Watchman_BTech_Project.git
cd Watchman_BTech_Project
```

## Step 2: Run the Installer

We have provided an automated script that handles the setup for you. This script will:
1. Update your system packages.
2. Install Python requirements (like FastAPI, Scikit-learn, Scapy).
3. Install Node.js (for the dashboard and Ganache local blockchain).
4. Create the `watchman` system service.

Run the installer:

```bash
sudo ./install.sh
```

> [!NOTE]
> The installer might take a few minutes as it downloads dependencies and sets up the virtual environment.

## Step 3: Verify the Installation

Once the installer finishes, check if the WatchMan Command Line Interface (CLI) is working:

```bash
watchman --help
```

You should see a list of available commands.

## Step 4: Start the Service

Start the WatchMan daemon in the background:

```bash
watchman start
```

Congratulations! WatchMan is now running on your system. It is actively monitoring your network interface and will block malicious IP addresses automatically.

## Next Steps

* Go to the **Dashboard** at `http://<your-server-ip>:8000/` to see live network stats.
* Read the [CLI.md](CLI.md) guide to learn how to manage the system.
