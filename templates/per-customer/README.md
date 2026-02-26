# Hardened per-customer Docker Compose

This template shows a minimal, hardened per-customer Docker Compose layout for Odoo.

Key points
- Run one stack per customer using a unique project name: `docker compose -p ${PROJECT_NAME}`.
- Do not expose Postgres to the host. Use internal networking and a reverse proxy for HTTP.
- Use `.env` (never committed) or Docker secrets for credentials.
- Use reverse-proxy labels (Traefik shown) to route traffic by hostname.

Quick start
1. Copy the example env: `cp .env.example .env` and edit values.
2. Start the stack:

```sh
docker compose -p "${PROJECT_NAME}" --env-file .env -f docker-compose.yml up -d
```

3. Configure your reverse proxy (Traefik or Nginx Proxy Manager) to handle `${PROJECT_HOST}`.

Backups
- Use the `backup` helper service to snapshot volumes, or run `pg_dump` from a dedicated backup host.
- Schedule and automate off-site sync (object storage, SharePoint, etc.) and test restores regularly.

Notes and recommendations
- Bind mounts of host source code should be read-only in production.
- Avoid bind-mounting the host `docker.sock` into application containers.
- Pin the `ODOO_IMAGE` to an immutable tag or digest for reproducible deployments.
- Consider using a single managed DB service for many small tenants or ensure proper resource isolation.
