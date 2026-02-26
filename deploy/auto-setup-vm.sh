#!/bin/bash
# Auto provision script for a fresh Ubuntu VM
# Usage: sudo bash auto-setup-vm.sh <git-repo-url> <install-dir> <domain>

set -e
if [[ $# -ne 3 ]]; then
  echo "Usage: $0 <git-repo-url> <install-dir> <domain>"
  exit 1
fi

GIT_URL=$1
dIR=$2
DOMAIN=$3

# clone or update repository
if [[ -d "$dIR" ]]; then
  echo "Updating existing repository at $dIR"
  cd "$dIR" && git pull
else
  git clone "$GIT_URL" "$dIR"
fi

# run base installer (native by default)
bash "$dIR/deploy/install-ubuntu.sh" -r "$GIT_URL" -d "$dIR" -D "$DOMAIN"

# install Odoo versions commonly used
for ver in 18.0 19.0 17.0; do
  bash "$dIR/deploy/install-ubuntu-native-odoo.sh" -v "$ver" || true
done

echo "Provisioned repository and Odoo installs."

echo "You can use provision-env.sh to create environments, e.g."
echo " sudo bash $dIR/deploy/provision-env.sh -n clientA -v 18.0"
