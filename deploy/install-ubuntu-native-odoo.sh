#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# Native Odoo Installation for Ubuntu 24.04
# Installs Odoo directly on the VM (no Docker) for faster environment creation
#
# Usage: ./install-ubuntu-native-odoo.sh [-v 17.0|18.0|19.0] [-d /opt/odoo] [--no-demo]
# Example: sudo ./install-ubuntu-native-odoo.sh -v 18.0 -d /opt/odoo

ODOO_VERSION="18.0"
INSTALL_BASE="/opt/odoo"
SKIP_DEMO=0
PG_USER="odoo"
PG_PASSWORD="odoo"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -v|--version) ODOO_VERSION="$2"; shift 2 ;;
    -d|--dir) INSTALL_BASE="$2"; shift 2 ;;
    --no-demo) SKIP_DEMO=1; shift 1 ;;
    --pg-user) PG_USER="$2"; shift 2 ;;
    --pg-password) PG_PASSWORD="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: $0 [-v odoo_version] [-d /opt/odoo] [--pg-user user] [--pg-password pass] [--no-demo]"
      echo "  -v, --version     Odoo version (default: 18.0). Supports: 16.0, 17.0, 18.0, 19.0"
      echo "  -d, --dir         Base installation directory (default: /opt/odoo)"
      echo "  --pg-user         PostgreSQL user (default: odoo)"
      echo "  --pg-password     PostgreSQL password (default: odoo)"
      echo "  --no-demo         Skip demo data on new databases"
      exit 0
      ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

ODOO_DIR="$INSTALL_BASE/odoo-$ODOO_VERSION"
VENV_DIR="$ODOO_DIR/.venv"
DATA_DIR="$INSTALL_BASE/data-$ODOO_VERSION"
LOG_DIR="/var/log/odoo"
CONF_DIR="/etc/odoo"
ADDONS_DIR="$INSTALL_BASE/custom-addons"

echo "=============================================="
echo "Native Odoo $ODOO_VERSION Installation"
echo "=============================================="
echo "Install dir: $ODOO_DIR"
echo "Data dir:    $DATA_DIR"
echo "Venv:        $VENV_DIR"
echo "=============================================="

# Determine Python version - Ubuntu 24.04 uses Python 3.12
# Detect what's available on the system
if command -v python3.12 &>/dev/null || apt-cache show python3.12 &>/dev/null; then
  PYTHON_VERSION="python3.12"
elif command -v python3.11 &>/dev/null || apt-cache show python3.11 &>/dev/null; then
  PYTHON_VERSION="python3.11"
elif command -v python3.10 &>/dev/null || apt-cache show python3.10 &>/dev/null; then
  PYTHON_VERSION="python3.10"
else
  PYTHON_VERSION="python3"
fi
echo "Using Python: $PYTHON_VERSION"

echo "==> Installing system dependencies..."
sudo apt update
sudo apt install -y \
  git curl wget \
  ${PYTHON_VERSION} ${PYTHON_VERSION}-venv ${PYTHON_VERSION}-dev \
  python3-pip python3-wheel python3-setuptools \
  build-essential libpq-dev libxml2-dev libxslt1-dev \
  libldap2-dev libsasl2-dev libjpeg-dev zlib1g-dev \
  libfreetype6-dev liblcms2-dev libwebp-dev \
  libffi-dev libssl-dev \
  postgresql postgresql-client \
  nodejs npm \
  wkhtmltopdf \
  fonts-liberation fonts-dejavu

# Install lessc globally for Odoo CSS compilation
sudo npm install -g less less-plugin-clean-css rtlcss

# Create odoo system user if not exists
if ! id -u odoo >/dev/null 2>&1; then
  echo "==> Creating system user 'odoo'"
  sudo adduser --system --group --home /opt/odoo --shell /bin/bash odoo
fi

# Setup PostgreSQL user
echo "==> Setting up PostgreSQL user..."
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='$PG_USER'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE USER $PG_USER WITH CREATEDB PASSWORD '$PG_PASSWORD';"

# Create directories
echo "==> Creating directories..."
sudo mkdir -p "$INSTALL_BASE" "$DATA_DIR" "$LOG_DIR" "$CONF_DIR" "$ADDONS_DIR"
sudo chown -R odoo:odoo "$INSTALL_BASE" "$DATA_DIR" "$LOG_DIR"
sudo chmod 755 "$CONF_DIR"

# Clone or update Odoo source
if [[ -d "$ODOO_DIR/.git" ]]; then
  echo "==> Odoo $ODOO_VERSION source exists — pulling updates..."
  sudo -u odoo git -C "$ODOO_DIR" fetch --all --prune
  sudo -u odoo git -C "$ODOO_DIR" checkout "$ODOO_VERSION" || true
  sudo -u odoo git -C "$ODOO_DIR" pull --rebase origin "$ODOO_VERSION" || true
else
  echo "==> Cloning Odoo $ODOO_VERSION from GitHub..."
  sudo -u odoo git clone --branch "$ODOO_VERSION" --depth 1 https://github.com/odoo/odoo.git "$ODOO_DIR"
fi

# Create virtualenv and install dependencies
echo "==> Setting up Python virtual environment..."
if [[ ! -d "$VENV_DIR" ]]; then
  sudo -u odoo $PYTHON_VERSION -m venv "$VENV_DIR"
fi

echo "==> Installing Python dependencies..."
sudo -u odoo "$VENV_DIR/bin/pip" install --upgrade pip wheel setuptools
sudo -u odoo "$VENV_DIR/bin/pip" install -r "$ODOO_DIR/requirements.txt"

# Additional useful packages
sudo -u odoo "$VENV_DIR/bin/pip" install psycopg2-binary python-ldap num2words phonenumbers

# Determine HTTP port based on version
case "$ODOO_VERSION" in
  16.0) HTTP_PORT=8066 ;;
  17.0) HTTP_PORT=8067 ;;
  18.0) HTTP_PORT=8068 ;;
  19.0) HTTP_PORT=8069 ;;
  *) HTTP_PORT=8069 ;;
esac

# Create Odoo configuration file
CONFIG_FILE="$CONF_DIR/odoo-$ODOO_VERSION.conf"
echo "==> Creating Odoo config at $CONFIG_FILE..."
sudo tee "$CONFIG_FILE" > /dev/null <<EOF
[options]
; Database settings
db_host = localhost
db_port = 5432
db_user = $PG_USER
db_password = $PG_PASSWORD

; Paths
addons_path = $ODOO_DIR/addons,$ODOO_DIR/odoo/addons,$ADDONS_DIR
data_dir = $DATA_DIR

; Server settings
http_port = $HTTP_PORT
longpolling_port = $((HTTP_PORT + 10))
xmlrpc_interface = 0.0.0.0
proxy_mode = True

; Logging
logfile = $LOG_DIR/odoo-$ODOO_VERSION.log
log_level = info
log_handler = :INFO

; Performance
workers = 2
max_cron_threads = 1
limit_memory_hard = 2684354560
limit_memory_soft = 2147483648
limit_time_cpu = 600
limit_time_real = 1200

; Security
admin_passwd = admin

; Demo data
without_demo = $([ "$SKIP_DEMO" -eq 1 ] && echo "True" || echo "False")
EOF

sudo chown root:odoo "$CONFIG_FILE"
sudo chmod 640 "$CONFIG_FILE"

# Create systemd service file
SERVICE_FILE="/etc/systemd/system/odoo-$ODOO_VERSION.service"
echo "==> Installing systemd service..."
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Odoo $ODOO_VERSION
Requires=postgresql.service
After=network.target postgresql.service

[Service]
Type=simple
SyslogIdentifier=odoo-$ODOO_VERSION
PermissionsStartOnly=true
User=odoo
Group=odoo
ExecStart=$VENV_DIR/bin/python $ODOO_DIR/odoo-bin -c $CONFIG_FILE
StandardOutput=journal+console
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "odoo-$ODOO_VERSION"

# Start the service
echo "==> Starting Odoo $ODOO_VERSION service..."
sudo systemctl start "odoo-$ODOO_VERSION" || true

cat <<EOF

======================================================
  Odoo $ODOO_VERSION Native Installation Complete!
======================================================

Odoo URL:       http://localhost:$HTTP_PORT
Config file:    $CONFIG_FILE
Service:        odoo-$ODOO_VERSION
Log file:       $LOG_DIR/odoo-$ODOO_VERSION.log

Commands:
  sudo systemctl status odoo-$ODOO_VERSION
  sudo systemctl restart odoo-$ODOO_VERSION
  sudo journalctl -u odoo-$ODOO_VERSION -f

Custom addons:  $ADDONS_DIR
Data directory: $DATA_DIR

To create a new database, visit http://localhost:$HTTP_PORT/web/database/manager

EOF
