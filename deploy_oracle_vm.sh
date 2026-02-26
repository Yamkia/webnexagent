#!/bin/bash
set -euo pipefail

# Simple idempotent deploy script for an Ubuntu VM.
# Usage: sudo bash deploy_oracle_vm.sh <git-repo-url> [target-dir]

REPO_URL=${1:-}
TARGET_DIR=${2:-webnexagent}

if [ -z "$REPO_URL" ]; then
  echo "Usage: sudo bash deploy_oracle_vm.sh <git-repo-url> [target-dir]"
  exit 1
fi

echo "Updating apt and installing prerequisites..."
apt update
apt install -y git curl ca-certificates

if ! command -v docker >/dev/null 2>&1; then
  echo "Installing Docker..."
  curl -fsSL https://get.docker.com -o get-docker.sh
  sh get-docker.sh
fi

echo "Installing Docker Compose plugin..."
apt-get install -y docker-compose-plugin || true

if [ ! -d "$TARGET_DIR" ]; then
  echo "Cloning repo into $TARGET_DIR"
  git clone "$REPO_URL" "$TARGET_DIR"
fi

cd "$TARGET_DIR"

echo "Starting containers with docker compose..."
# Prefer `docker compose` (plugin); fall back to docker-compose if needed
if docker compose version >/dev/null 2>&1; then
  docker compose up -d --build
else
  if command -v docker-compose >/dev/null 2>&1; then
    docker-compose up -d --build
  else
    echo "docker compose not available; install docker-compose or docker compose plugin"
    exit 2
  fi
fi

echo "Deployment finished. Check containers with: docker ps"
