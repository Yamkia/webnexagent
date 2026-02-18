#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# Usage: ./install-ubuntu.sh -r <git-repo-url> [-b branch] [-d /opt/webnexagent] [-D domain] [--no-certbot]
# Example: sudo ./install-ubuntu.sh -r git@github.com:yourorg/webnexagent.git -d /opt/webnexagent -D example.com

REPO_URL=""
BRANCH="main"
INSTALL_DIR="/opt/webnexagent"
DOMAIN=""
SKIP_CERTBOT=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -r|--repo) REPO_URL="$2"; shift 2 ;;
    -b|--branch) BRANCH="$2"; shift 2 ;;
    -d|--dir) INSTALL_DIR="$2"; shift 2 ;;
    -D|--domain) DOMAIN="$2"; shift 2 ;;
    --no-certbot) SKIP_CERTBOT=1; shift 1 ;;
    -h|--help) echo "Usage: $0 -r <git-repo-url> [-b branch] [-d /opt/webnexagent] [-D domain] [--no-certbot]"; exit 0 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

if [[ -z "$REPO_URL" ]]; then
  echo "ERROR: --repo is required (git clone URL)" >&2
  exit 2
fi

echo "==> Installing OS packages (apt)..."
sudo apt update
sudo apt install -y git python3.12-venv python3.12-dev python3-pip build-essential libpq-dev nginx curl

if [[ "$SKIP_CERTBOT" -eq 0 ]]; then
  sudo apt install -y certbot python3-certbot-nginx || true
fi

# Create service user
if ! id -u webnex >/dev/null 2>&1; then
  echo "==> Creating system user 'webnex'"
  sudo adduser --system --group --no-create-home webnex
fi

# Clone or update repository
if [[ -d "$INSTALL_DIR/.git" ]]; then
  echo "==> Repo already exists at $INSTALL_DIR — pulling changes"
  sudo git -C "$INSTALL_DIR" fetch --all --prune
  sudo git -C "$INSTALL_DIR" checkout "$BRANCH" || true
  sudo git -C "$INSTALL_DIR" pull --rebase origin "$BRANCH"
else
  echo "==> Cloning $REPO_URL -> $INSTALL_DIR"
  sudo mkdir -p "$INSTALL_DIR"
  sudo chown "$USER":"$USER" "$INSTALL_DIR"
  git clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
fi

# Create virtualenv and install requirements
echo "==> Setting up Python virtualenv"
python3.12 -m venv "$INSTALL_DIR/.venv"
source "$INSTALL_DIR/.venv/bin/activate"
python -m pip install --upgrade pip wheel
pip install -r "$INSTALL_DIR/requirements.txt"

# Ensure correct ownership
sudo chown -R webnex:webnex "$INSTALL_DIR"

# Install systemd unit
echo "==> Installing systemd unit"
sudo cp "$INSTALL_DIR/deploy/systemd/webnex.service" /etc/systemd/system/webnex.service
sudo systemctl daemon-reload
sudo systemctl enable --now webnex

# Install nginx config
echo "==> Installing nginx config"
sudo cp "$INSTALL_DIR/deploy/nginx/webnex.conf" /etc/nginx/sites-available/webnex
if [[ ! -e /etc/nginx/sites-enabled/webnex ]]; then
  sudo ln -s /etc/nginx/sites-available/webnex /etc/nginx/sites-enabled/webnex
fi
sudo nginx -t && sudo systemctl reload nginx

# Optional: obtain TLS certificate
if [[ -n "$DOMAIN" && "$SKIP_CERTBOT" -eq 0 ]]; then
  echo "==> Obtaining TLS certificate for $DOMAIN (certbot)"
  sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m admin@$DOMAIN || true
fi

cat <<'EOF'

==> DONE
- App installed at: $INSTALL_DIR
- Service: sudo systemctl status webnex
- Logs: sudo journalctl -u webnex -f

Next steps:
1) Edit the .env file at $INSTALL_DIR/.env and fill in your API keys (or set LLM_PROVIDER="none").
2) Restart: sudo systemctl restart webnex
3) Check: curl http://127.0.0.1:5001/health
EOF
