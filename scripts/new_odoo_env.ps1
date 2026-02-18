param(
    [Parameter(Mandatory = $true)][string]$Name,
    [ValidateSet('17.0','18.0','19.0')][string]$Version = '17.0',
    [string]$PgHost = 'localhost',
    [int]$PgPort = 5432,
    [string]$PgUser = 'odoo',
    [string]$PgPassword = 'odoo',
    [string]$PgBin = '',
    [string]$AdminPassword = 'admin',
    [string[]]$Modules = @(),
    [string]$WebsiteDesign = '',
    [int]$HttpPort = 8069,
    [switch]$SkipInit,
    [switch]$StorePassword
)

$ErrorActionPreference = 'Stop'

function Ensure-Directory {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$EnvDir = Join-Path $RepoRoot "environments\$Name"
$LogDir = Join-Path $RepoRoot 'logs'
Ensure-Directory $EnvDir
Ensure-Directory $LogDir

# Locate or fetch Odoo sources
$OdooPath = $null
if ($Version -eq '17.0' -and (Test-Path (Join-Path $RepoRoot 'odoo-community-17\odoo-bin'))) {
    $OdooPath = Join-Path $RepoRoot 'odoo-community-17'
} elseif ($Version -eq '17.0' -and (Test-Path (Join-Path $RepoRoot 'odoo-source\odoo-bin'))) {
    $OdooPath = Join-Path $RepoRoot 'odoo-source'
} else {
    $Target = Join-Path $RepoRoot "odoo-$Version"
    if (-not (Test-Path (Join-Path $Target 'odoo-bin'))) {
        Write-Host "Cloning Odoo $Version ..."
        git clone --depth 1 --branch $Version https://github.com/odoo/odoo.git $Target
    }
    $OdooPath = $Target
}

$VenvPath = Join-Path $RepoRoot ".venv-$Version"
if (-not (Test-Path (Join-Path $VenvPath 'Scripts\python.exe'))) {
    Write-Host "Creating venv at $VenvPath"
    py -3.11 -m venv $VenvPath
}

Write-Host "Upgrading pip and installing requirements for Odoo $Version"
& (Join-Path $VenvPath 'Scripts\python.exe') -m pip install --upgrade pip
& (Join-Path $VenvPath 'Scripts\pip.exe') install -r (Join-Path $OdooPath 'requirements.txt')

# Create DB and role (assumes provided credentials can create DBs)
# ensure we have the venv python path for fallback
$PythonExe = Join-Path $VenvPath 'Scripts\python.exe'

$env:PGPASSWORD = $PgPassword
$psqlCmd = $null
# Allow explicitly providing the PostgreSQL bin or a direct psql.exe path via -PgBin
if ($PgBin -and $PgBin.Trim() -ne '') {
    $candidate = $PgBin
    if (-not (Test-Path $candidate)) { $candidate = Join-Path $PgBin 'psql.exe' -ErrorAction SilentlyContinue }
    if (Test-Path $candidate) { $psqlCmd = $candidate }
}

# If not found via -PgBin, try the PATH and common install locations
if (-not $psqlCmd) {
    $psqlCmdInfo = Get-Command psql -ErrorAction SilentlyContinue
    if ($psqlCmdInfo) { $psqlCmd = $psqlCmdInfo.Source }
}

if (-not $psqlCmd) {
    $possible = @( 'C:\\Program Files\\PostgreSQL\\18\\bin\\psql.exe', 'C:\\Program Files\\PostgreSQL\\15\\bin\\psql.exe' )
    foreach ($p in $possible) {
        if (Test-Path $p) { $psqlCmd = $p; break }
    }
}
if (-not $psqlCmd) {
    Write-Host "Warning: 'psql' not found in PATH. Will attempt Python fallback to create DB/role using the virtualenv Python."
    $dbExists = $null
    # Attempt Python fallback using venv python and psycopg2 (installed via requirements)
    try {
        $pyScriptPath = Join-Path $EnvDir '._create_db_fallback.py'
        $pyScript = @"
import sys
import traceback
try:
    import psycopg2
    from psycopg2 import sql
    conn = psycopg2.connect(host='$PgHost', port=$PgPort, user='$PgUser', password='$PgPassword')
    conn.autocommit = True
    cur = conn.cursor()
    # create role if not exists (note: requires superuser privileges)
    try:
        cur.execute(sql.SQL("CREATE USER {user} WITH PASSWORD %s CREATEDB;").format(user=sql.Identifier('$PgUser')), ['$PgPassword'])
    except Exception:
        pass
    # create database if not exists
    try:
        cur.execute(sql.SQL("SELECT 1 FROM pg_database WHERE datname=%s;"), ['$Name'])
        exists = cur.fetchone()
        if not exists:
            cur.execute(sql.SQL("CREATE DATABASE {db} OWNER {owner};").format(db=sql.Identifier('$Name'), owner=sql.Identifier('$PgUser')))
    except Exception as e:
        print('DB creation error:', e)
    cur.close()
    conn.close()
    print('Python fallback: attempted DB/role creation (check Postgres privileges).')
except Exception as e:
    traceback.print_exc()
    sys.exit(2)
"@

        $pyScript | Set-Content -Path $pyScriptPath -Encoding ASCII
        & $PythonExe $pyScriptPath
        Remove-Item $pyScriptPath -ErrorAction SilentlyContinue
    } catch {
        Write-Host "Python fallback failed: $_"
    }
} else {
    Write-Host "Using psql at: $psqlCmd"

    # Quick check that psql runs and report its version for diagnostics
    try {
        $psqlVersion = & $psqlCmd '--version' 2>&1
        Write-Host "psql reported: $psqlVersion"
    } catch {
        Write-Host "psql execution failed while checking --version: $_"
        Write-Host "Troubleshooting: ensure '$psqlCmd' is executable and that PostgreSQL is running."
        Write-Host "Try: `"$psqlCmd`" --version"
        throw
    }

    try {
        # Use argument array to avoid quoting issues on Windows when invoking external executables
        $dbExists = & $psqlCmd @('-h', $PgHost, '-p', "$PgPort", '-U', $PgUser, '-tAc', "SELECT 1 FROM pg_database WHERE datname='$Name'" ) 2>$null
    } catch {
        $dbExists = $null
    }

    if (-not $dbExists) {
        Write-Host "Creating database $Name with owner $PgUser"
        $createSql = "CREATE DATABASE \"$Name\" OWNER \"$PgUser\";"
        try {
            & $psqlCmd @('-h', $PgHost, '-p', "$PgPort", '-U', $PgUser, '-c', $createSql) | Out-Null
        } catch {
            Write-Host "psql call failed: $_"
            Write-Host "Troubleshooting: try running the following commands in an elevated PowerShell to see full output and create the DB/role manually if needed:"
            Write-Host "`"$psqlCmd`" -h $PgHost -p $PgPort -U $PgUser -c `"$createSql`""
            Write-Host "`"$psqlCmd`" -U postgres -c `"CREATE USER $PgUser WITH PASSWORD '$PgPassword' CREATEDB;`""
            Write-Host "`"$psqlCmd`" -U postgres -c `"CREATE DATABASE $Name OWNER $PgUser;`""
            throw
        }
    }
}

# Write environment-specific config
$ConfPath = Join-Path $EnvDir 'odoo.conf'
$LogPath = Join-Path $LogDir "${Name}-${Version}.log"
$PythonExe = Join-Path $VenvPath 'Scripts\python.exe'
$OdooBinPath = Join-Path $OdooPath 'odoo-bin'
$RunCmd = "`"$PythonExe`" `"$OdooBinPath`" -c `"$ConfPath`" -d $Name"
$AddonsPath = @(
    Join-Path $OdooPath 'odoo\addons'
    Join-Path $RepoRoot 'addons'
    Join-Path $RepoRoot 'deployable_brand_theme'
) -join ','

# Normalize module list (include website design if provided and not 'default')
if ($WebsiteDesign -and $WebsiteDesign.Trim() -ne '' -and $WebsiteDesign.Trim().ToLower() -ne 'default') {
    $Modules += $WebsiteDesign.Trim()
}
$Modules = $Modules | Where-Object { $_ -and $_.Trim() -ne '' } | Select-Object -Unique

$DbPasswordLine = "db_password = $PgPassword"

@"
[options]
db_host = $PgHost
db_port = $PgPort
db_user = $PgUser
$DbPasswordLine
dbfilter = ^$Name$
db_name = $Name
addons_path = $AddonsPath
logfile = $LogPath
http_port = $HttpPort
; Uncomment and set a strong master password for database management
admin_passwd = $AdminPassword
"@ | Set-Content -Path $ConfPath -Encoding ASCII

# Per-environment README for tracking
$ReadmePath = Join-Path $EnvDir 'README.md'
$PgNote = "(db_password stored in odoo.conf)"

@"
# Odoo environment: $Name
- Version: $Version
- Database: $Name
- Config: environments/$Name/odoo.conf
- Log: logs/${Name}-${Version}.log
- Odoo path: $OdooPath
- Virtualenv: $VenvPath
- DB password handling: $PgNote
- Admin login/password: admin / $AdminPassword
- Modules installed: $([string]::Join(', ', $Modules))
- Website design: $WebsiteDesign

Run Odoo:
    $RunCmd

If the password is not stored in odoo.conf, set PGPASSWORD in your shell before running:
    $env:PGPASSWORD='$PgPassword'
    $RunCmd
"@ | Set-Content -Path $ReadmePath -Encoding ASCII

if (-not $SkipInit) {
    Write-Host "Initializing Odoo database $Name (base module)"
    & $PythonExe $OdooBinPath -c $ConfPath -d $Name -i base --stop-after-init

    if ($Modules.Count -gt 0) {
        $modStr = ($Modules -join ',')
        Write-Host "Installing modules: $modStr"
        & $PythonExe $OdooBinPath -c $ConfPath -d $Name -i $modStr --stop-after-init
    }
}

Write-Host "Environment ready. Run Odoo with:"
Write-Host "`n$RunCmd`n"

# Record the environment in env_history.json for the web UI to pick up immediately.
$EnvHistoryPath = Join-Path $RepoRoot 'env_history.json'
try {
    $entry = @{
        db_name = $Name
        port = $HttpPort
        odoo_version = $Version
        url = "http://localhost:$HttpPort"
        created_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    }

    $envs = @()
    if (Test-Path $EnvHistoryPath) {
        try {
            $raw = Get-Content $EnvHistoryPath -Raw -ErrorAction Stop
            if ($raw.Trim() -ne '') {
                $envs = $raw | ConvertFrom-Json -ErrorAction Stop
            }
        } catch {
            Write-Host "Warning: failed to read existing env_history.json, will recreate it."
            $envs = @()
        }
    }

    if ($envs -eq $null) { $envs = @() }

    # Remove any existing entry with same db_name and port
    $envs = $envs | Where-Object { -not ( ($_.db_name -eq $entry.db_name) -and ($_.port -eq $entry.port) ) }

    # Prepend the new entry so newest appear first
    $newList = @($entry) + @($envs)

    $newList | ConvertTo-Json -Depth 5 | Set-Content -Path $EnvHistoryPath -Encoding UTF8
    Write-Host "Updated env_history.json with environment $Name (port $HttpPort)."
} catch {
    Write-Host "Failed to update env_history.json: $_"
}
