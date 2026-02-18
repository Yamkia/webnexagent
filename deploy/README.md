Deploy files for running Web-Nexus Agent on Ubuntu 24.04

Quick start (example):

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
