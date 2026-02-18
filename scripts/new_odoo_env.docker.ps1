param(
    [Parameter(Mandatory = $true)][string]$Name,
    [ValidateSet('17.0','18.0','19.0')][string]$Version = '17.0',
    [int]$HttpPort = 8069,
    [string]$PgUser = 'odoo',
    [string]$PgPassword = 'odoo',
    [string]$PgHost = 'db',
    [int]$PgPort = 5432,
    [string]$AdminPassword = 'admin',
    [string]$SqlDump = ''  # Optional path to a SQL dump to restore into the created DB
)

$ErrorActionPreference = 'Stop'

function Ensure-Directory { param([string]$Path) if (-not (Test-Path $Path)) { New-Item -ItemType Directory -Path $Path | Out-Null } }

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$EnvDir = Join-Path $RepoRoot "environments\$Name"
Ensure-Directory $EnvDir

# Create a small docker-compose file for this environment
$ComposePath = Join-Path $EnvDir 'docker-compose.yml'
$compose = @"
version: '3.8'

services:
  odoo-$Name:
    image: odoo:$Version
    environment:
      POSTGRES_HOST: $PgHost
      POSTGRES_USER: $PgUser
      POSTGRES_PASSWORD: $PgPassword
    ports:
      - "$HttpPort:8069"
    volumes:
      - ../../addons:/mnt/extra-addons
      - ../../deployable_brand_theme:/mnt/brand_theme
      - odoo_${Name}_data:/var/lib/odoo
    depends_on:
      - db

volumes:
  odoo_${Name}_data:
"@

Set-Content -Path $ComposePath -Value $compose -Encoding UTF8

# Write a minimal odoo.conf (helpful for reference and local runs)
$ConfPath = Join-Path $EnvDir 'odoo.conf'
$conf = @"
[options]
db_host = $PgHost
db_port = $PgPort
db_user = $PgUser
db_password = $PgPassword
dbfilter = ^$Name$
db_name = $Name
addons_path = /mnt/extra-addons,/mnt/brand_theme
logfile = /var/log/odoo/$Name.log
http_port = $HttpPort
admin_passwd = $AdminPassword
"@
Set-Content -Path $ConfPath -Value $conf -Encoding UTF8

# Per-environment README
$ReadmePath = Join-Path $EnvDir 'README.md'
$readme = @"
# Odoo environment: $Name
- Version: $Version
- Database: $Name
- Config: environments/$Name/odoo.conf
- Compose: environments/$Name/docker-compose.yml
- Url: http://localhost:$HttpPort

Run with (from repository root):
    docker-compose -f environments/$Name/docker-compose.yml up

"@
Set-Content -Path $ReadmePath -Value $readme -Encoding UTF8

# --- Attempt to create the database in the root Postgres container (if available) ---
$composeFile = Join-Path $RepoRoot 'docker-compose.yml'

function _run_compose {
    param([string[]]$Args)
    try {
        $out = & docker compose -f $composeFile @Args 2>&1
        return @{ success = $true; output = $out }
    } catch {
        try {
            $out = & docker-compose -f $composeFile @Args 2>&1
            return @{ success = $true; output = $out }
        } catch {
            return @{ success = $false; output = $null }
        }
    }
}

Write-Host "Checking for Postgres service (root compose: $composeFile)..."
$ps = _run_compose -Args @('ps','-q','db')
if (-not $ps.success -or [string]::IsNullOrWhiteSpace($ps.output)) {
    Write-Host "Postgres service not found or not running. Attempting to start 'db' service in root compose..."
    $up = _run_compose -Args @('up','-d','db')
    if (-not $up.success) { Write-Host "Failed to start db service via docker compose. Please ensure docker compose is installed and your root compose is accessible." }
    else { Start-Sleep -Seconds 3 }
}

# Check if DB exists
$check = _run_compose -Args @('exec','-T','db','psql','-U',$PgUser,'-tAc',"SELECT 1 FROM pg_database WHERE datname='$Name';")
if ($check.success -and $check.output -and $check.output.Trim() -eq '1') {
    Write-Host "Database '$Name' already exists in Postgres."
} else {
    Write-Host "Attempting to create database '$Name' in Postgres container..."
    $create = _run_compose -Args @('exec','-T','db','psql','-U',$PgUser,'-c',"CREATE DATABASE \"$Name\" OWNER $PgUser;")
    if ($create.success) { Write-Host "Database '$Name' created." } else { Write-Host "Failed to create database. Output: $($create.output)" }
}

# Optional SQL restore
if ($SqlDump -and (Test-Path $SqlDump)) {
    Write-Host "Restoring SQL dump '$SqlDump' into database '$Name'..."
    $cid = $null
    try { $cid = & docker compose -f $composeFile ps -q db 2>$null } catch { }
    if (-not $cid) { try { $cid = & docker-compose -f $composeFile ps -q db 2>$null } catch { } }
    if ($cid -and $cid.Trim() -ne '') {
        $tmp = "/tmp/$(Split-Path $SqlDump -Leaf)"
        & docker cp $SqlDump "$cid:$tmp"
        & docker exec -i $cid psql -U $PgUser -d $Name -f $tmp
        Write-Host "SQL restore attempted. Check Postgres logs for details."
    } else {
        Write-Host "Could not determine Postgres container id; skipping SQL restore. You can restore manually using psql into the db container."
    }
}

# Update env_history.json so the web app can discover the environment
$EnvHistoryPath = Join-Path $RepoRoot 'env_history.json'
$entry = @{ db_name = $Name; port = $HttpPort; odoo_version = $Version; url = "http://localhost:$HttpPort"; created_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") }

$envs = @()
if (Test-Path $EnvHistoryPath) {
    try {
        $raw = Get-Content $EnvHistoryPath -Raw -ErrorAction Stop
        if ($raw.Trim() -ne '') { $envs = $raw | ConvertFrom-Json -ErrorAction Stop }
    } catch {
        Write-Host "Warning: failed to read existing env_history.json, will recreate it."
        $envs = @()
    }
}

if ($envs -eq $null) { $envs = @() }

# Remove any existing entry with same db_name and port
$envs = $envs | Where-Object { -not ( ($_.db_name -eq $entry.db_name) -and ($_.port -eq $entry.port) ) }

$newList = @($entry) + @($envs)
$newList | ConvertTo-Json -Depth 5 | Set-Content -Path $EnvHistoryPath -Encoding UTF8

Write-Host "Created Docker-based Odoo environment '$Name' (port $HttpPort) under 'environments/$Name'."
Write-Host "Start it with: docker-compose -f environments/$Name/docker-compose.yml up"
