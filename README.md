# Web-Nexus Agent

This repository contains the Web-Nexus Agent application and supporting environment automation for Odoo and related services.

## Overview

The app is a Flask-based UI for managing Odoo environments, agent workflows, and automation. It can be run locally via Python or containerized with Docker Compose.

## Prerequisites

- Python 3.11+ (3.12 recommended)
- Git
- Docker and Docker Compose (for container mode)
- A `.env` file for configuration values

## Local setup

1. Create and activate a Python virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Create a `.env` or `.env.development` file in the repository root. Example:

   ```env
   APP_ENV=development
   FLASK_RUN_HOST=0.0.0.0
   FLASK_RUN_PORT=5001
   FLASK_DEBUG=True
   LLM_PROVIDER=none
   ```

   If you want the AI agent to work, add provider keys such as:

   ```env
   OPENAI_API_KEY=sk-...
   LLM_PROVIDER=openai
   ```

   For Docker and Odoo service variables, use:

   ```env
   POSTGRES_USER=odoo
   POSTGRES_PASSWORD=odoo
   ```

4. Start the Flask app:

   ```powershell
   python app.py
   ```

5. Open the UI in your browser:

   ```text
   http://localhost:5001
   ```

## Run with Docker Compose

This repository includes `docker-compose.yml` to start the app together with PostgreSQL and Odoo containers.

1. Build and start services:

   ```powershell
   docker compose up -d --build
   ```

2. Check logs:

   ```powershell
   docker compose logs -f web
   ```

3. Access the UI:

   ```text
   http://localhost:5001
   ```

### Services included

- `web`: the Flask UI and automation server
- `db`: PostgreSQL database
- `odoo-17`: Odoo 17 container
- `odoo-18`: Odoo 18 container
- `odoo-19`: Odoo 19 container
- `proxy`: Nginx reverse proxy for port 80

If you only want to run the app without the Odoo containers, you can start just the web service:

```powershell
docker compose up -d web db
```

## Environment files

The app loads configuration from `.env` by default. It also supports environment-specific files when `APP_ENV` or `ENVIRONMENT` is set, for example:

- `.env.development`
- `.env.production`
- `.env.staging`

If `APP_ENV=development`, the app will prefer `.env.development` first.

## Helpful commands

- Activate the venv:
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```
- Install dependencies:
  ```powershell
  pip install -r requirements.txt
  ```
- Run locally:
  ```powershell
  python app.py
  ```
- Build and run with Docker:
  ```powershell
  docker compose up -d --build
  ```
- Stop containers:
  ```powershell
  docker compose down
  ```

## Notes

- If AI features are not working, set `LLM_PROVIDER=none` to disable the agent and avoid provider errors.
- The app uses session-based login and stores user accounts in `users.json`.
- The UI exposes health endpoints at `/health` and `/ready`.

## Troubleshooting

- If the app does not start, confirm that `requirements.txt` dependencies are installed in the active venv.
- If Docker push or build fails, ensure Docker Desktop is running and the current folder contains `docker-compose.yml`.
- For environment-specific settings, verify the correct `.env` file is present and contains valid values.
