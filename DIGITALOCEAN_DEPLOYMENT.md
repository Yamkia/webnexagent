# DigitalOcean Deployment Guide

This document describes how to deploy the `webnexagent` app to a DigitalOcean Droplet using Docker Compose, plus how to update the app when code changes.

## 1. Server access

Use your SSH key to connect to the droplet:

```powershell
ssh -i $env:USERPROFILE\.ssh\id_ed25519_new ubuntu@162.243.214.43
```

If the key is passphrase protected, enter the passphrase when prompted.

## 2. Clone the repository on the server

If the repo is not yet on the server, clone it:

```bash
cd ~
git clone https://github.com/Yamkia/webnexagent.git webnexagent
cd webnexagent
```

If the repo already exists, go to the folder:

```bash
cd ~/webnexagent
```

## 3. Install Docker (if needed)

If Docker is not installed on the droplet yet, install it using the official script:

```bash
sudo curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu
```

Then disconnect and reconnect:

```bash
exit
ssh -i $env:USERPROFILE\.ssh\id_ed25519_new ubuntu@162.243.214.43
cd ~/webnexagent
```

## 4. Start the app with Docker Compose

Make sure you are inside the repository folder first:

```bash
cd ~/webnexagent
```

Then start the stack:

```bash
docker compose up -d
```

This starts the full stack defined in `docker-compose.yml`, including:

- `web` service on port `5001`
- Odoo 17 on port `8069`
- Odoo 18 on port `8070`
- Odoo 19 on port `8071`
- nginx proxy on port `80` (port `443` only if HTTPS certs are configured)

## 5. Verify that the app is running

Check container status:

```bash
cd ~/webnexagent
docker compose ps
```

Follow logs:

```bash
docker compose logs -f
```

Or just watch the web service:

```bash
docker compose logs -f web
```

## 6. Access URLs

Depending on the service you want:

- `http://162.243.214.43:5001` — main web app
- `http://162.243.214.43:8069` — Odoo 17
- `http://162.243.214.43:8070` — Odoo 18
- `http://162.243.214.43:8071` — Odoo 19
- `http://162.243.214.43` — nginx/HTTP proxy (HTTPS on `https://162.243.214.43` only if certs are configured)

## 7. Update workflow for code changes

### Option A: Use Git

1. Make changes locally.
2. Commit and push to GitHub:

```bash
git add .
git commit -m "Describe changes"
git push origin main
```

3. On the droplet:

```bash
cd ~/webnexagent
git pull
docker compose up -d --build
```

If only the app code changed and the container is bind-mounted, you may only need:

```bash
docker compose restart web
```

### Option B: Copy local changes directly

If you do not want to use Git, copy the repo from your local machine to the server and then restart the container.

Example with `scp`:

```powershell
scp -r -i $env:USERPROFILE\.ssh\id_ed25519_new C:\Users\<you>\Documents\webnexagent ubuntu@162.243.214.43:/home/ubuntu/webnexagent
```

Then on the droplet:

```bash
cd ~/webnexagent
docker compose restart web
```

## 8. Important notes

- Always run `docker compose up -d` from inside `~/webnexagent`.
- Local Windows edits do not automatically sync into the server unless you push/copy them.
- The server-side `web` container sees files from `/home/ubuntu/webnexagent`.

## 9. Troubleshooting

### `docker compose up -d` says "no configuration file provided"

This means you are not in the repository folder. Run:

```bash
cd ~/webnexagent
docker compose up -d
```

### Docker commands require sudo or group membership

If Docker commands fail, make sure the `ubuntu` user is in the `docker` group, then reconnect:

```bash
sudo usermod -aG docker ubuntu
exit
ssh -i $env:USERPROFILE\.ssh\id_ed25519_new ubuntu@162.243.214.43
```

---

This guide can be shared with teammates for the full deploy/update workflow on DigitalOcean.