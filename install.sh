#!/usr/bin/env bash
set -e
cat << "EOF"

██╗    ██╗ █████╗ ████████╗ ██████╗██╗  ██╗███╗   ███╗ █████╗ ███╗   ██╗
██║    ██║██╔══██╗╚══██╔══╝██╔════╝██║  ██║████╗ ████║██╔══██╗████╗  ██║
██║ █╗ ██║███████║   ██║   ██║     ███████║██╔████╔██║███████║██╔██╗ ██║
██║███╗██║██╔══██║   ██║   ██║     ██╔══██║██║╚██╔╝██║██╔══██║██║╚██╗██║
╚███╔███╔╝██║  ██║   ██║   ╚██████╗██║  ██║██║ ╚═╝ ██║██║  ██║██║ ╚████║
 ╚══╝╚══╝ ╚═╝  ╚═╝   ╚═╝    ╚═════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝

       Machine Learning + Blockchain Network Intrusion Detection System
                    Version 1.0.0
           Developed as Ribert Kandi Junior

EOF



if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (e.g. sudo ./install.sh)"
  exit 1
fi

echo "[1/7] Verifying Environment..."
if ! command -v python3 &> /dev/null; then
    echo "Python3 is not installed. Please install it first."
    exit 1
fi
if ! command -v pip3 &> /dev/null; then
    echo "pip3 is not installed. Installing python3-pip..."
    apt-get update && apt-get install -y python3-pip python3-venv
fi

echo "[2/7] Standardizing Filesystem..."
mkdir -p /etc/watchman
mkdir -p /var/log/watchman
mkdir -p /var/lib/watchman
mkdir -p /opt/watchman/models
if [ -d "models" ]; then
    cp -r models/* /opt/watchman/models/ || true
fi
mkdir -p /tmp/watchman

# Create dedicated user
if ! id "watchman" &>/dev/null; then
    useradd -r -s /bin/false watchman
fi

echo "[3/7] Setting up Python Environment..."
INSTALL_DIR="/opt/watchman/app"
mkdir -p $INSTALL_DIR
cp -r . $INSTALL_DIR
cd $INSTALL_DIR

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .

echo "[4/7] Configuring Database and Permissions..."
chown -R watchman:watchman /etc/watchman
chown -R watchman:watchman /var/log/watchman
chown -R watchman:watchman /var/lib/watchman
chown -R watchman:watchman /opt/watchman/models
chown -R watchman:watchman $INSTALL_DIR

echo "[5/7] Creating Default Admin Account..."
# Run the installation command as the watchman user
sudo -u watchman bash -c "source $INSTALL_DIR/.venv/bin/activate && watchman install"

echo "[6/7] Setting up Systemd Service and CLI..."
ln -sf /opt/watchman/app/.venv/bin/watchman /usr/local/bin/watchman
cp watchman.service /etc/systemd/system/
systemctl daemon-reload
# Removed auto-start per user request
# systemctl enable watchman.service

echo "[7/7] Installation finalized."
# systemctl start watchman.service

echo "=========================================="
echo " Installation Complete!"
echo " The daemon is currently stopped."
echo " To start it, run: sudo watchman start"
echo " Use 'watchman configure' to update settings."
echo "=========================================="
