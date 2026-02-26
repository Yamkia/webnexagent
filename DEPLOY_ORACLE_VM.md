# Deploying this Odoo project to an Oracle Cloud Always‑Free VM

This guide shows a minimal, low-cost way to run your Odoo Community edition from this repository on an Oracle Cloud Always‑Free VM (or any small Ubuntu VM). It focuses on using Docker Compose to run Odoo + Postgres and a reverse proxy for HTTPS.

## Summary
- Use an always‑free VM (Ubuntu 22.04 LTS recommended).
- Install Docker and the Docker Compose plugin.
- Clone this repo and run `docker compose up -d`.
- Use a reverse proxy (nginx or Caddy) for SSL (Let's Encrypt).
- Keep Postgres internal to the Docker network and perform backups.

## Prerequisites
- Oracle Cloud account with Always‑Free compute (or any small Linux VM provider).
- SSH key and access to the VM.
- (Optional) Domain name for SSL.

## Instance selection
- Choose an Ubuntu 22.04 LTS image and a small VM shape from the Always‑Free options. If the provider only offers ARM (Ampere) instances, ensure any Docker images you run are ARM-compatible or build from source.

## Network / Firewall
Open these ports to the world (or restrict by IP where appropriate):
- `22` SSH (restrict to your IP if possible)
- `80` and `443` for HTTP/HTTPS (or only `443` if you redirect)
- `8069` Odoo (you can keep Odoo behind the reverse proxy and not expose 8069)

Do NOT open Postgres (5432) publicly. Keep it internal to the Docker network.

## Quick manual deploy steps (recommended)
1. SSH into the VM (replace `<user>` and `<ip>`):

```bash
ssh <user>@<public_ip>
```

2. Install Docker & Docker Compose plugin, then clone the repo:

```bash
sudo apt update
sudo apt install -y git curl
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER || true
newgrp docker || true
sudo apt-get install -y docker-compose-plugin

# clone your repo (replace URL)
git clone <your-repo-url> webnexagent
cd webnexagent
```

3. Edit any environment files or `odoo.conf` as needed (set DB user/password, admin password, etc.).

4. Start the stack:

```bash
sudo docker compose up -d --build
```

Notes:
- If your Docker on the VM uses the older `docker-compose` binary, use `docker-compose up -d`.
- Make sure `docker-compose.yml` in this repo is configured to create a Postgres container or point to an external Postgres.

## Reverse proxy and HTTPS
Option A — Caddy (simplest):

```bash
docker run --name caddy -d -p 80:80 -p 443:443 \
  -v caddy_data:/data -v caddy_config:/config \
  -v /path/to/Caddyfile:/etc/caddy/Caddyfile \
  caddy:latest
```

Option B — nginx + certbot (more control)
- Run an nginx container or install nginx on the host; use Certbot to obtain TLS certs; configure nginx to proxy `/` to `localhost:8069`.

## Backups
- Dump Postgres periodically:

```bash
docker exec -t <postgres_container> pg_dumpall -c -U <postgres_user> > /backup/db-$(date +%F).sql
```

- Backup the Odoo filestore (usually `filestore` directory in the data volume).
- Store backups on object storage (OCI Object Storage, S3, or rsync to another host).

## Restore quick notes
- To restore DB: `psql -U <user> -f db-YYYY-MM-DD.sql postgres` inside the Postgres container.
- Copy filestore back into the volume mount location and set proper permissions.

## Security & hardening
- Use strong DB passwords and `admin_passwd` in `odoo.conf`.
- Do not expose Postgres; keep it on the Docker network.
- Use a firewall to restrict SSH by IP.
- Keep Docker images and the OS updated.

## Optional: Automated deploy script
- See `deploy_oracle_vm.sh` at the repo root for an idempotent script that installs Docker, clones the repo and starts `docker compose`.

If you want, I can:
- Walk you through creating the specific VM in Oracle Cloud UI with screenshots, or
- Customize the `docker-compose.yml` in this repo to ensure it's production-ready (reverse-proxy, volumes, env file, backups).

-- End

## OCI New Console — Create an Always‑Free VM (step‑by‑step)

Follow these steps in the OCI New Console to create a VM you can use to run this project.

1. Sign in to the Oracle Cloud Console and confirm your tenancy and region in the top-right (your screenshot shows "South Africa Central").

2. From the Home page you can click `Create a VM instance` in the Build panel (or open the hamburger menu → Compute → Instances → Create Instance).

3. On the Create Instance page:
  - Give the instance a name (example: `webnexagent-odoo`).
  - Under *Image and shape* choose an Ubuntu LTS image (Ubuntu 22.04 recommended).
  - For *Shape*, open the shape chooser and filter/select a shape marked *Always Free Eligible* (or use the default recommended shape if you don't see that option). If you plan to run multiple Odoo versions choose the largest Always‑Free option available.

4. Networking and SSH keys:
  - Use the default Virtual Cloud Network (VCN) and Subnet unless you need a custom network.
  - Assign a public IP (Ephemeral is fine for testing; choose Reserved/Public if you want a stable address).
  - Add your SSH public key in the SSH keys section so you can `ssh` into the instance.

5. Configure the boot volume and other options if needed (default sizes usually work; increase only if you expect large filestores).

6. Create the instance. Wait until state shows *Running*.

7. Open firewall rules (Network Security Group or Security Lists):
  - Ensure TCP ports `22` (SSH), `80` (HTTP) and `443` (HTTPS) are allowed from the internet.
  - Do NOT open `5432` (Postgres) to the public — keep Postgres internal. If you need to debug you may temporarily open it, but close it afterwards.

8. SSH into the VM from your machine (replace with your user and public IP):

```bash
ssh ubuntu@<public_ip>
```

9. On the VM run the included deploy script to install Docker, clone the repo and start containers:

```bash
sudo bash deploy_oracle_vm.sh <your-repo-git-url>
```

10. After `docker compose up -d` completes, verify the stack:

```bash
docker ps
sudo docker compose logs -f
```

11. If you used the nginx proxy (added to `docker-compose.yml`), mount SSL certs into `/etc/ssl/certs/fullchain.pem` and `/etc/ssl/private/privkey.pem` on the proxy container, or run a companion container (Certbot or Caddy) to manage Let's Encrypt certificates automatically.

Troubleshooting & tips
- If the VM shape is ARM (Ampere) and you used x86 images, either rebuild images for ARM or pick an x86 Always‑Free shape.
- Reserve the public IP in the console if you want a stable address for DNS.
- Consider enabling automatic backups or schedule DB dumps to OCI Object Storage.

If you want I can now:
- Walk you through these console steps interactively while you do them, or
- Reserve a public IP and provide the exact `ssh` command and the `docker compose` commands to run once your VM is ready.

