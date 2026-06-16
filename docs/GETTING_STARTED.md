# Getting Started with WatchMan NIDS

This guide will walk you through the installation and initial setup of WatchMan NIDS.

## Prerequisites

Before you begin, ensure you have the following installed on your system:
- **Python 3.8+** (Added to PATH)
- **Node.js 16+** and **npm**
- **Git**
- **Npcap** or **WinPcap** (required by Scapy on Windows for packet capturing)
- **Administrator/Root privileges** (required for capturing network packets)

## Installation

### 1. Clone the Repository
```bash
git clone <repository_url>
cd Watchman_BTech_Project
```

### 2. Set Up the Python Environment
Create and activate a virtual environment:
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows)
.venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Set Up the Node.js Environment
Install dependencies for the Electron frontend:
```bash
npm install
```

### 4. Initialize the Database and Admin User
Use the CLI to initialize the system. This creates the `alerts.db` database and configures the default administrator account.
```bash
python src/cli.py install
```

## First Run

### 1. Start the Backend API Server
Run the FastAPI backend using the CLI:
```bash
python src/cli.py start
```
The server will start at `http://127.0.0.1:5000`.

### 2. Launch the Electron Desktop App
Open a new terminal, navigate to the project root, and run:
```bash
npm start
```
This will open the WatchMan NIDS dashboard.

### 3. Login
Use the default credentials to log in:
- **Username**: `admin`
- **Password**: `watchman2026`

### 4. Start Packet Capture
Once logged in, you can start network monitoring from the dashboard or by using the backend API.
*(Note: Packet capture requires administrative privileges. Make sure your backend terminal is running as an Administrator.)*
