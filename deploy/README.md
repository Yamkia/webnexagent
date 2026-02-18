Deploy files for running Web-Nexus Agent on Ubuntu 24.04

## Deployment Options

| Approach | Speed | Best For |
|----------|-------|----------|
| Native VM | **Fastest** | Production, fast env creation |
| Docker Compose | Medium | Development, isolation |

---

## Option 1: Native VM (Recommended for Production)

This approach runs Odoo directly on the VM without Docker overhead, resulting in **5-10x faster environment creation**.

### Step 1: Install Webnexagent

```bash
sudo bash ./deploy/install-ubuntu.sh -r <GIT_URL> -d /opt/webnexagent -D your.domain.example
```

### Step 2: Install Native Odoo (one or more versions)

```bash
# Install Odoo 18.0
sudo bash /opt/webnexagent/deploy/install-ubuntu-native-odoo.sh -v 18.0

# Install Odoo 17.0 (optional)
sudo bash /opt/webnexagent/deploy/install-ubuntu-native-odoo.sh -v 17.0

# Install Odoo 19.0 (optional)
sudo bash /opt/webnexagent/deploy/install-ubuntu-native-odoo.sh -v 19.0
```

### Step 3: Create Environments Instantly

Use the provision script to create new Odoo environments in seconds:

```bash
# Create a new environment named "clientA" on Odoo 18.0
sudo bash /opt/webnexagent/deploy/provision-env.sh -n clientA -v 18.0

# Create another environment with a specific port
sudo bash /opt/webnexagent/deploy/provision-env.sh -n clientB -v 18.0 -p 8101
```

Or use the web API:

```bash
curl -X POST http://localhost:5001/envs/create \
  -H "Content-Type: application/json" \
  -d '{"name": "clientA", "version": "18.0", "type": "native"}'
```

### Native Environment Management

```bash
# List running environments
curl http://localhost:5001/envs

# Start an environment
sudo systemctl start odoo-18.0-clientA

# Stop an environment
sudo systemctl stop odoo-18.0-clientA

# View logs
sudo journalctl -u odoo-18.0-clientA -f

# Check status of all Odoo services
systemctl list-units 'odoo-*' --all
```

### Directory Structure

```
/opt/odoo/
├── odoo-17.0/           # Odoo 17 source + venv
├── odoo-18.0/           # Odoo 18 source + venv
├── odoo-19.0/           # Odoo 19 source + venv
├── data-18.0/           # Data directories per version
│   └── envs/
│       ├── clientA/
│       └── clientB/
└── custom-addons/       # Shared custom addons

/etc/odoo/
├── odoo-18.0.conf       # Base Odoo 18 config
└── envs/                # Per-environment configs
    ├── 18.0-clientA.conf
    └── 18.0-clientB.conf

/var/log/odoo/           # All Odoo logs
```

---

## Option 2: Docker Compose (Containerised)

Use this approach for development or when you need container isolation.

### Quick start (example):

1) On your VM, run (replace <GIT_URL> and <DOMAIN>):

   sudo bash -c "./install-ubuntu.sh -r <GIT_URL> -d /opt/webnexagent -D your.domain.example"

2) Edit the .env at `/opt/webnexagent/.env` and add API keys (or set LLM_PROVIDER="none").
3) Start/inspect the service:

   sudo systemctl restart webnex
   sudo journalctl -u webnex -f

Notes:
- The installer creates a system user `webnex`, places the app in `/opt/webnexagent`,
  installs a systemd unit and nginx site, and (optionally) obtains a TLS cert via certbot.
- If your Git remote requires SSH access, ensure the VM has the deploy key or uses an account
  that can clone the repository.
- The install script is idempotent; re-running will update the repo and restart the service.

### Docker Compose (containerised VM deploy)

- Use `deploy/install-ubuntu-docker.sh` to provision an Ubuntu 24.04 VM with Docker + Docker Compose
  and run the app via the repository's `docker-compose.yml` (systemd unit `webnex-docker` is installed).

Quick Docker steps (example):

1) On the VM:

   sudo bash -c "./deploy/install-ubuntu-docker.sh -r <GIT_URL> -d /opt/webnexagent -D your.domain.example"

2) Edit the `.env` at `/opt/webnexagent/.env` and add secrets/API keys.
3) Use the production compose override (removes host bind-mounts):

   sudo docker compose -f /opt/webnexagent/docker-compose.yml -f /opt/webnexagent/docker-compose.prod.yml up -d --build

4) Service & logs:

   sudo systemctl restart webnex-docker
   sudo journalctl -u webnex-docker -f

Notes:
- The `docker` installer will add the `webnex` user to the `docker` group.
- For production-grade DBs consider using a managed/remote Postgres rather than exposing 5432 on the VM.
- If you prefer the non-container approach, continue to use `deploy/install-ubuntu.sh` (systemd + venv).

---

## Environment Variables

Set these in `/opt/webnexagent/.env`:

```bash
# For native Odoo installations
ODOO_INSTALL_BASE=/opt/odoo        # Base directory for Odoo installations
WEBNEX_DIR=/opt/webnexagent        # Webnexagent directory for custom addons

# Agent configuration
LLM_PROVIDER=openai                # or anthropic, azure, etc.
OPENAI_API_KEY=sk-...
```

## Switching Between Native and Docker

The app auto-detects the best mode:
- If native Odoo is installed → uses native (faster)
- If only Docker is available → uses Docker

Force a specific mode via the API:

```bash
# Force Docker
curl -X POST http://localhost:5001/envs/create \
  -d '{"name": "test", "version": "18.0", "type": "docker"}'

# Force Native
curl -X POST http://localhost:5001/envs/create \
  -d '{"name": "test", "version": "18.0", "type": "native"}'
```

## Performance Comparison

| Operation | Docker | Native VM |
|-----------|--------|-----------|
| Create new env | ~2-3 min | ~10-30 sec |
| Start env | ~30 sec | ~2-3 sec |
| Stop env | ~10 sec | ~1 sec |
| Memory overhead | +500MB | None |

