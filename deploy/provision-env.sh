#!/usr/bin/env bash
set -euo pipefail

# Quick Odoo Environment Provisioning Script
# Creates a new Odoo environment (database + config) in seconds
#
# Usage: ./provision-env.sh -n <env_name> [-v 18.0] [-p 8080]
# Example: ./provision-env.sh -n clientA -v 18.0 -p 8080

ENV_NAME=""
ODOO_VERSION="18.0"
HTTP_PORT=""
DB_NAME=""
ADMIN_PASSWORD="admin"
INSTALL_MODULES=""
PG_USER="odoo"
PG_PASSWORD="odoo"
INSTALL_BASE="/opt/odoo"
WEBNEX_DIR="/opt/webnexagent"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -n|--name) ENV_NAME="$2"; shift 2 ;;
    -v|--version) ODOO_VERSION="$2"; shift 2 ;;
    -p|--port) HTTP_PORT="$2"; shift 2 ;;
    -d|--database) DB_NAME="$2"; shift 2 ;;
    -m|--modules) INSTALL_MODULES="$2"; shift 2 ;;
    --admin-password) ADMIN_PASSWORD="$2"; shift 2 ;;
    --pg-user) PG_USER="$2"; shift 2 ;;
    --pg-password) PG_PASSWORD="$2"; shift 2 ;;
    --webnex-dir) WEBNEX_DIR="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: $0 -n <env_name> [-v odoo_version] [-p http_port] [-d db_name] [-m modules]"
      echo ""
      echo "Options:"
      echo "  -n, --name           Environment name (required)"
      echo "  -v, --version        Odoo version (default: 18.0)"
      echo "  -p, --port           HTTP port (auto-assigned if not specified)"
      echo "  -d, --database       Database name (defaults to env_name)"
      echo "  -m, --modules        Comma-separated list of modules to install"
      echo "  --admin-password     Admin password (default: admin)"
      echo "  --webnex-dir         Webnexagent directory for custom addons"
      exit 0
      ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

if [[ -z "$ENV_NAME" ]]; then
  echo "ERROR: --name is required" >&2
  exit 1
fi

# Set defaults
DB_NAME="${DB_NAME:-$ENV_NAME}"
INSTANCE_NAME="$ODOO_VERSION-$ENV_NAME"
ODOO_DIR="$INSTALL_BASE/odoo-$ODOO_VERSION"
VENV_DIR="$ODOO_DIR/.venv"
CONF_DIR="/etc/odoo/envs"
DATA_DIR="$INSTALL_BASE/data-$ODOO_VERSION"
LOG_DIR="/var/log/odoo"

# Auto-assign port if not specified (find next available)
if [[ -z "$HTTP_PORT" ]]; then
  BASE_PORT=8100
  for ((p=BASE_PORT; p<8200; p++)); do
    if ! ss -tuln | grep -q ":$p "; then
      HTTP_PORT=$p
      break
    fi
  done
fi

echo "=============================================="
echo "Provisioning Odoo Environment: $ENV_NAME"
echo "=============================================="
echo "Version:    $ODOO_VERSION"
echo "Database:   $DB_NAME"
echo "HTTP Port:  $HTTP_PORT"
echo "=============================================="

# Check if Odoo base is installed
if [[ ! -d "$ODOO_DIR" ]]; then
  echo "ERROR: Odoo $ODOO_VERSION not installed at $ODOO_DIR"
  echo "Run: sudo ./install-ubuntu-native-odoo.sh -v $ODOO_VERSION"
  exit 1
fi

# Create config directory
sudo mkdir -p "$CONF_DIR"
sudo chown root:odoo "$CONF_DIR"

# Build addons path
ADDONS_PATH="$ODOO_DIR/addons,$ODOO_DIR/odoo/addons,$INSTALL_BASE/custom-addons"

# Add webnex custom addons if they exist
if [[ -d "$WEBNEX_DIR/addons" ]]; then
  for subdir in "$WEBNEX_DIR/addons"/*; do
    [[ -d "$subdir" ]] && ADDONS_PATH="$ADDONS_PATH,$subdir"
  done
fi
[[ -d "$WEBNEX_DIR/deployable_brand_theme" ]] && ADDONS_PATH="$ADDONS_PATH,$WEBNEX_DIR/deployable_brand_theme"
[[ -d "$WEBNEX_DIR/custom_modules" ]] && ADDONS_PATH="$ADDONS_PATH,$WEBNEX_DIR/custom_modules"

# Create environment-specific config
CONFIG_FILE="$CONF_DIR/$INSTANCE_NAME.conf"
echo "==> Creating config: $CONFIG_FILE"

sudo tee "$CONFIG_FILE" > /dev/null <<EOF
[options]
; Database settings
db_host = localhost
db_port = 5432
db_user = $PG_USER
db_password = $PG_PASSWORD
db_name = $DB_NAME
dbfilter = ^${DB_NAME}$

; Paths
addons_path = $ADDONS_PATH
data_dir = $DATA_DIR/envs/$ENV_NAME

; Server settings
http_port = $HTTP_PORT
longpolling_port = $((HTTP_PORT + 100))
xmlrpc_interface = 0.0.0.0
proxy_mode = True

; Logging
logfile = $LOG_DIR/$INSTANCE_NAME.log
log_level = info

; Performance (single env - lighter resources)
workers = 2
max_cron_threads = 1
limit_memory_hard = 1610612736
limit_memory_soft = 1073741824
limit_time_cpu = 300
limit_time_real = 600

; Security
admin_passwd = $ADMIN_PASSWORD
list_db = False

; Features
without_demo = True
EOF

sudo chown root:odoo "$CONFIG_FILE"
sudo chmod 640 "$CONFIG_FILE"

# Create data directory for this env
sudo mkdir -p "$DATA_DIR/envs/$ENV_NAME"
sudo chown -R odoo:odoo "$DATA_DIR/envs/$ENV_NAME"

# Create the database
echo "==> Creating database: $DB_NAME"
if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
  echo "Database '$DB_NAME' already exists, skipping creation."
else
  sudo -u postgres createdb -O "$PG_USER" "$DB_NAME"
  echo "Database '$DB_NAME' created."
fi

# Create systemd service for this environment
SERVICE_FILE="/etc/systemd/system/odoo-$INSTANCE_NAME.service"
echo "==> Creating systemd service: odoo-$INSTANCE_NAME"

sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Odoo $ODOO_VERSION - $ENV_NAME
Requires=postgresql.service
After=network.target postgresql.service

[Service]
Type=simple
SyslogIdentifier=odoo-$INSTANCE_NAME
User=odoo
Group=odoo
ExecStart=$VENV_DIR/bin/python $ODOO_DIR/odoo-bin -c $CONFIG_FILE
StandardOutput=journal+console
Restart=on-failure
RestartSec=5
TimeoutStopSec=60

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "odoo-$INSTANCE_NAME"

# Initialize the database with base module
echo "==> Initializing Odoo database..."
sudo -u odoo "$VENV_DIR/bin/python" "$ODOO_DIR/odoo-bin" \
  -c "$CONFIG_FILE" \
  -d "$DB_NAME" \
  -i base \
  --stop-after-init \
  --no-http

# Install additional modules if specified
if [[ -n "$INSTALL_MODULES" ]]; then
  echo "==> Installing modules: $INSTALL_MODULES"
  sudo -u odoo "$VENV_DIR/bin/python" "$ODOO_DIR/odoo-bin" \
    -c "$CONFIG_FILE" \
    -d "$DB_NAME" \
    -i "$INSTALL_MODULES" \
    --stop-after-init \
    --no-http
fi

# Start the service
echo "==> Starting Odoo environment..."
sudo systemctl start "odoo-$INSTANCE_NAME"

# Update webnex env_history.json if available
ENV_JSON="$WEBNEX_DIR/env_history.json"
if [[ -f "$ENV_JSON" ]]; then
  echo "==> Registering environment in webnexagent..."
  # Use Python to safely update JSON
  python3 - <<PYEOF
import json
import os
from datetime import datetime

env_file = "$ENV_JSON"
new_entry = {
    "db_name": "$DB_NAME",
    "port": $HTTP_PORT,
    "odoo_version": "$ODOO_VERSION",
    "url": "http://localhost:$HTTP_PORT",
    "type": "native",
    "service": "odoo-$INSTANCE_NAME",
    "config": "$CONFIG_FILE",
    "created_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
}

try:
    with open(env_file, 'r') as f:
        envs = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    envs = []

# Remove existing entry with same name
envs = [e for e in envs if e.get('db_name') != new_entry['db_name']]
envs.insert(0, new_entry)

with open(env_file, 'w') as f:
    json.dump(envs, f, indent=2)

print(f"Updated {env_file}")
PYEOF
fi

cat <<EOF

======================================================
  Environment '$ENV_NAME' Provisioned Successfully!
======================================================

URL:            http://localhost:$HTTP_PORT
Database:       $DB_NAME
Config:         $CONFIG_FILE
Service:        odoo-$INSTANCE_NAME

Commands:
  sudo systemctl status odoo-$INSTANCE_NAME
  sudo systemctl restart odoo-$INSTANCE_NAME
  sudo journalctl -u odoo-$INSTANCE_NAME -f

First login credentials:
  User:     admin
  Password: admin

EOF
