#!/bin/sh
set -e

# Provision script for Odoo container (odoo-18)
# Env vars used:
#  - AUTO_INIT (true/false) - enable provisioning
#  - INIT_DB_NAME - name of DB to create
#  - INIT_MODULES - comma-separated module names to install
#  - INIT_MODULE_GITS - space-separated git urls for modules to clone into /mnt/extra-addons
#  - POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD

HOST=${POSTGRES_HOST:-db}
USER=${POSTGRES_USER:-odoo}
PASS=${POSTGRES_PASSWORD:-odoo}

clone_modules() {
  if [ -n "$INIT_MODULE_GITS" ]; then
    echo "Cloning modules from INIT_MODULE_GITS..."
    for url in $INIT_MODULE_GITS; do
      name=$(basename "$url" .git)
      dest="/mnt/extra-addons/$name"
      if [ -d "$dest" ]; then
        echo "Module $name already exists, skipping clone"
      else
        echo "Cloning $url -> $dest"
        git clone "$url" "$dest" || echo "git clone failed for $url"
      fi
    done
  fi
}

wait_for_db() {
  echo "Waiting for Postgres at $HOST..."
  until pg_isready -h "$HOST" -U "$USER" >/dev/null 2>&1; do
    sleep 1
  done
}

create_and_install() {
  DBNAME="$INIT_DB_NAME"
  MODULES="$INIT_MODULES"
  if [ -z "$DBNAME" ]; then
    echo "No INIT_DB_NAME provided, skipping DB creation"
    return
  fi
  echo "Checking if DB $DBNAME exists..."
  exists=$(psql -h "$HOST" -U "$USER" -tAc "SELECT 1 FROM pg_database WHERE datname='$DBNAME';")
  if [ "$exists" = "1" ]; then
    echo "Database $DBNAME already exists, skipping creation/install"
    return
  fi
  echo "Creating DB $DBNAME and installing modules: $MODULES"
  # Create DB
  psql -h "$HOST" -U "$USER" -c "CREATE DATABASE \"$DBNAME\" OWNER \"$USER\";"
  # Run Odoo to install modules into new DB
  if [ -n "$MODULES" ]; then
    echo "Running Odoo to install modules..."
    su -s /bin/sh odoo -c "odoo -d $DBNAME -i $MODULES --stop-after-init"
  else
    echo "No INIT_MODULES specified; DB created but no modules installed"
  fi
}

# Only run provisioning when AUTO_INIT is set to 'true'
if [ "${AUTO_INIT:-false}" = "true" ]; then
  echo "AUTO_INIT is true: running provisioning"
  clone_modules
  wait_for_db
  create_and_install
else
  echo "AUTO_INIT not enabled; skipping provisioning"
fi

# Exec the default command (starts the Odoo server)
exec "$@"
