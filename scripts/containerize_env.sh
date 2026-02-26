#!/usr/bin/env bash
# containerize_env.sh
# Usage: ./containerize_env.sh <env_name> [version] [image_tag] [registry] [mode]
# mode: development|staging|production (defaults to development)
# Example: ./containerize_env.sh mysite 19.0 webnex/mysite:19.0 ghcr.io/myorg
set -euo pipefail
PROJ_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NAME="$1"
VERSION="${2:-19.0}"
IMAGE_ARG="${3:-}"
REGISTRY="${4:-}"
MODE_ARG="${5:-}"
ENV_MODE="${MODE_ARG:-${APP_ENV:-development}}"

if [ -z "$NAME" ]; then
  echo "Usage: $0 <env_name> [version] [image_tag] [registry]"
  exit 2
fi

# Choose build context based on Odoo version
BUILD_CTX="${PROJ_ROOT}/docker/odoo-19-provision"
if [[ "$VERSION" == 18.* || "$VERSION" == "18" ]]; then
  BUILD_CTX="${PROJ_ROOT}/docker/odoo-18-provision"
fi

IMAGE_TAG="${IMAGE_ARG:-webnex/odoo-${NAME}:${VERSION}-${ENV_MODE}}"
if [ -n "$REGISTRY" ]; then
  IMAGE_TAG="$REGISTRY/${IMAGE_TAG##*/}"
fi

echo "Building image $IMAGE_TAG from context $BUILD_CTX"
docker build -t "$IMAGE_TAG" "$BUILD_CTX"

# Create environment folder and compose file
ENV_DIR="$PROJ_ROOT/environments/$NAME"
mkdir -p "$ENV_DIR"
COMPOSE_FILE="$ENV_DIR/docker-compose.yml"

cat > "$COMPOSE_FILE" <<EOF
version: '3.8'

services:
  odoo-${NAME}:
    image: ${IMAGE_TAG}
    # Prefer using an env_file to pick up .env.development/.env.staging/.env.production
    env_file: ../../.env.${ENV_MODE}
    environment:
      POSTGRES_HOST: db
      POSTGRES_USER: \\${POSTGRES_USER:-odoo}
      POSTGRES_PASSWORD: \\${POSTGRES_PASSWORD:-odoo}
    ports:
      - "8069:8069"
    volumes:
      - ../../addons:/mnt/extra-addons
      - ../../deployable_brand_theme:/mnt/brand_theme
      - odoo_${NAME}_data:/var/lib/odoo
    depends_on:
      - db

volumes:
  odoo_${NAME}_data:
EOF

echo "Wrote $COMPOSE_FILE"

echo "Containerized environment '$NAME' ready. To run it:"
echo "  docker compose -f $COMPOSE_FILE up -d"

echo "To push the built image (if registry specified):"
if [ -n "$REGISTRY" ]; then
  echo "  docker push $IMAGE_TAG"
fi
