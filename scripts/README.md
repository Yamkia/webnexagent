Containerize environment scripts

Scripts:
- containerize_env.sh - Bash script to build an Odoo image and write a per-environment docker-compose at `environments/<name>/docker-compose.yml`.
- containerize_env.ps1 - PowerShell equivalent for Windows hosts.

Usage examples:

# Build and create a compose for 'mysite' using Odoo 19, default image tag
./scripts/containerize_env.sh mysite 19.0

# To specify mode (development|staging|production):
./scripts/containerize_env.sh mysite 19.0 "" "" staging

# Specify image tag and registry, then push
./scripts/containerize_env.sh mysite 19.0 ghcr.io/myorg/mysite:19.0 ghcr.io/myorg

after running, start the environment:

docker compose -f environments/mysite/docker-compose.yml up -d

Notes:
- The scripts choose a build context in `docker/odoo-19-provision` or `docker/odoo-18-provision` depending on `Version`.
- For production, set `APP_ENV=production` (or `ENVIRONMENT=production`) and use a private registry or CI/CD to push images.
 - The scripts accept an optional `mode` parameter (development|staging|production). When provided, the generated `environments/<name>/docker-compose.yml` will include `env_file: ../../.env.<mode>` so the environment picks the correct `.env` file.
