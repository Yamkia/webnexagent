# Docker deployment (Quick start)

## Prerequisites
- Docker Desktop (Windows: WSL2 backend recommended)
- At least 8GB free disk and enough RAM (Odoo + Postgres can be memory-hungry)

## Quick start (development mode)
1. Copy `.env.example` to `.env` and edit the values if needed.
2. Build and run the stack:

```bash
docker-compose up --build
```

3. Open the web UI at: http://localhost:5001
4. Odoo instances will be available at:
   - Odoo 17: http://localhost:8069
   - Odoo 18: http://localhost:8070
   - Odoo 19: http://localhost:8071

## Per-version addons and custom modules
- Each Odoo version mounts a separate addons folder so you can develop version-specific modules:
  - `./addons/17` → Odoo 17
  - `./addons/18` → Odoo 18
  - `./addons/19` → Odoo 19
- Add your custom module code to the appropriate folder and restart that Odoo container (or update apps list from the Odoo UI). Example:
  - To restart Odoo 18: `docker-compose restart odoo-18`
- If you prefer shared modules across versions, place them in `deployable_brand_theme` or create a shared `./addons/shared` and bind-mount it into any service you're using (edit `docker-compose.yml` accordingly).

## Notes
- The `web` service uses a bind mount (`./:/srv/app`) so changes on your laptop are visible immediately inside the container.
- To run fully immutable images (production-style), remove the bind mount and build the app image, then run `docker-compose up --build -d`.

### Build-time vs. bind-mount tradeoffs 💡
- Bind-mount (development): you edit files on your host and the container sees changes immediately — fast iteration, no need to rebuild. However, the host filesystem is sent as build context only when building an image; large repos can slow `docker build` dramatically. Use bind-mounts with `docker compose up` for day-to-day development.
- Image build (production): building an image creates a reproducible artifact and isolates runtime from host. Build-time steps (like installing system deps) happen inside the image — if your repo contains large source trees (e.g., local Odoo checkouts), add them to `.dockerignore` to avoid long transfers. When adding or changing dependencies or Dockerfile changes, you must rebuild the image (`--build`).

- If you need optional system packages (e.g., for audio support), the `Dockerfile` supports a build-arg `INSTALL_AUDIO_DEPS=true` to include `ffmpeg`, `libasound2-dev`, and `portaudio19-dev` necessary to build `pyaudio`. When building with audio support run:

```bash
# Build with audio deps (includes pyaudio via requirements-audio.txt)
docker compose build --build-arg INSTALL_AUDIO_DEPS=true
``` 

If you do not enable audio deps, `pyaudio` will be skipped during image build (so the build will succeed without portaudio headers).
- If you expect frequent Dockerfile changes and want faster builds, consider using a small build context (via `.dockerignore`) or leveraging a multi-stage build that copies only required files into the final image.

## Migrating local Postgres DBs
- To import an existing DB dump into the Postgres container:

```bash
cat dump.sql | docker exec -i <compose_project>_db_1 psql -U $POSTGRES_USER -d $POSTGRES_DB
```

Replace `<compose_project>` with the project name shown by `docker-compose ps` (or use `-p <name>` when running compose).

## Running the helper script
- Use `scripts\new_odoo_env.docker.ps1` to create an environment scaffolding (a small `docker-compose.yml` for the env) and record it in `env_history.json` so the web UI can discover it.

### Automatic DB provisioning and optional restore
- You can optionally have the script attempt to create the Postgres database inside the root `db` service and restore from a SQL dump:

```powershell
.\
ew_odoo_env.docker.ps1 -Name myenv -Version 17.0 -HttpPort 8070 -SqlDump C:\path\to\dump.sql
```

- The script will attempt to start the `db` service (via `docker compose -f docker-compose.yml up -d db`) if it's not running, then create the database and restore the dump if supplied. If automated restore fails, you'll see an explanatory message and can restore manually into the Postgres container using `psql`.

### Creating modules quickly
- Use `scripts\add_module.ps1` to create a module scaffold under a specific version:

```powershell
.\scripts\add_module.ps1 -ModuleName my_module -Version 18 -Restart
```

- This creates `addons/18/my_module` with minimal files and (with `-Restart`) restarts the matching Odoo container so the new module is discovered.


## Disabling the LLM agent
If you do not want to use an LLM provider (no API keys), set `LLM_PROVIDER="none"` in your `.env` file. The application will run with the agent disabled and the UI will still be usable. Example:

```bash
# in your .env
LLM_PROVIDER="none"
```

After changing `.env`, restart the `web` service:

```bash
docker compose up -d --no-deps --force-recreate web
```

### Production server & moving out of OneDrive (recommended)
- Run the web app under Gunicorn and disable the Flask debug reloader for more stable and faster responses in containers. We added `gunicorn` to `requirements.txt` and `/health` and `/ready` endpoints to help with readiness and pre-warming.

- If your project is stored in OneDrive (or other syncing folders), move it to WSL2 or a non-synced local folder to avoid bind-mount I/O slowness:
  - In WSL2: `wsl git clone <repo>` into your WSL home (e.g., `/home/<user>/projects/webnexagent`) and run Docker from WSL or configure Docker Desktop to use WSL2 backend.
  - On Windows (non-OneDrive): clone into `C:\projects\webnexagent` and run `docker compose up` there.

Both changes (Gunicorn + non-OneDrive location) together give the biggest improvement for dev responsiveness.

---
