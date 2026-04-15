# Sync local Odoo module assets to Zisanda Hub with Rclone + OneDrive

This guide sets up sync from a local repo to a OneDrive remote, then optionally into Docker containers for Odoo.

## 1. Recommended local project layout

Root local folder (example): `C:\Users\<you>\Documents\zisandahub`

- `addons/` : general custom modules
- `customers/` : client-specific white-labeling/themes

You can also use `C:\projects\zisandahub` or any path, as long as subdirs are as above.

## 2. Install Rclone

1. Download from https://rclone.org/downloads
2. Install or unpack, and ensure `rclone` is in your PATH.

## 3. Configure OneDrive remote

1. Open terminal / cmd / PowerShell.
2. Run:

```powershell
rclone config
```

3. Type `n` for New Remote.
4. Remote name: `zisandahub_remote`
5. When prompted for storage type, choose `onedrive` (or the number for Microsoft OneDrive).
6. Leave `client_id` blank (press Enter).
7. Leave `client_secret` blank (press Enter).
8. `Edit advanced config?` -> `n`
9. `Use auto config?` -> `y` (browser opens for login and consent)
10. `Is that a OneDrive Personal or Business?` -> choose the suggested type (personal/business as appropriate)
11. It will detect account/drives; choose the correct drive number and confirm `y`.

## 4. Find rclone config file

```powershell
rclone config file
```

Note the path, e.g. `%USERPROFILE%\.config\rclone\rclone.conf`.

## 5. Verify remote works

```powershell
rclone ls zisandahub_remote:
```

If it lists files (or returns nothing but no error), remote is ready.

## 6. Sync local folder to OneDrive

### Initial upload (one-way sync local -> remote)

```powershell
rclone sync "C:\Users\<you>\Documents\zisandahub" "zisandahub_remote:zisandahub" --progress
```

### Dry-run first (strongly recommended)

```powershell
rclone sync "C:\Users\<you>\Documents\zisandahub" "zisandahub_remote:zisandahub" --dry-run --progress
```

### Regular updates

```powershell
rclone sync "C:\Users\<you>\Documents\zisandahub" "zisandahub_remote:zisandahub" --progress
```

## 7. Optional: sync from OneDrive back to local (if server changes are allowed)

```powershell
rclone sync "zisandahub_remote:zisandahub" "C:\Users\<you>\Documents\zisandahub" --progress
```

## 8. Docker / Zisanda Hub integration (local development)

In `docker-compose.yml`, mount your local `addons` and `customers` paths for Odoo services:

```yaml
services:
  odoo-19:
    ...
    volumes:
      - ./addons/19:/mnt/extra-addons
      - ./customers:/mnt/customers
      - ./bluewave_theme:/mnt/extra-addons/bluewave_theme
      - ./deployable_brand_theme:/mnt/brand_theme
```

For OneDrive path sync, keep your local `zisandahub` folder as source and bind-mount that into container.

## 9. Cron / scheduled sync (Windows Task Scheduler / Linux cron)

- Windows: create task running `rclone sync ...` every 5 min or 1h.
- Linux: `crontab -e`, e.g.: `*/15 * * * * /usr/bin/rclone sync /path/to/zisandahub zisandahub_remote:zisandahub --log-file /var/log/rclone-sync.log`

## 10. Safety notes

- `rclone sync` is destructive: remote destination is made an exact copy of source (deletes extra files).
- Use `--dry-run` before production run.
- Keep backups before batch deletes.
