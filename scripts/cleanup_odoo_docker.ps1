<#
cleanup_odoo_docker.ps1

Lists Docker containers, volumes and networks with names containing "odoo" and optionally removes them.
Also optionally calls the local web UI endpoint `/odoo/local_env/drop_all` to let the app clean environments first.

Usage examples:
  # Dry-run: list resources
  .\cleanup_odoo_docker.ps1

  # Call app endpoint (replace PORT) then remove resources interactively
  .\cleanup_odoo_docker.ps1 -Port 5070 -CallAppDrop

  # Remove without calling app endpoint (interactive confirmation)
  .\cleanup_odoo_docker.ps1 -Force

Note: This script runs Docker commands on your machine. Inspect before running.
#>
param(
    [int]$Port = 5070,
    [switch]$CallAppDrop,
    [switch]$Force
)

function List-Containers {
    Write-Host "\n=== Containers matching 'odoo' ===" -ForegroundColor Cyan
    $containers = docker ps -a --filter "name=odoo" --format "{{.ID}}`t{{.Names}}`t{{.Image}}" 2>$null
    if (!$containers) {
        Write-Host "No containers found matching 'odoo'."
    } else {
        $containers | ForEach-Object { Write-Host $_ }
    }
    return $containers
}

function List-Volumes {
    Write-Host "\n=== Volumes containing 'odoo' ===" -ForegroundColor Cyan
    $vols = docker volume ls --format "{{.Name}}" 2>$null | Select-String -Pattern "odoo" | ForEach-Object { $_.ToString().Trim() }
    if (!$vols) {
        Write-Host "No volumes found matching 'odoo'."
    } else {
        $vols | ForEach-Object { Write-Host $_ }
    }
    return $vols
}

function List-Networks {
    Write-Host "\n=== Networks containing 'odoo' ===" -ForegroundColor Cyan
    $nets = docker network ls --format "{{.ID}} {{.Name}}" 2>$null | Select-String -Pattern "odoo" | ForEach-Object { $_.ToString().Trim() }
    if (!$nets) {
        Write-Host "No networks found matching 'odoo'."
    } else {
        $nets | ForEach-Object { Write-Host $_ }
    }
    return $nets
}

function Call-AppDropAll {
    param($port)
    $url = "http://localhost:$port/odoo/local_env/drop_all"
    Write-Host "\nCalling app endpoint: $url" -ForegroundColor Yellow
    try {
        $resp = Invoke-RestMethod -Uri $url -Method Post -TimeoutSec 30
        Write-Host "App response:" -ForegroundColor Green
        $resp | ConvertTo-Json -Depth 4 | Write-Host
    } catch {
        Write-Host "Failed to call app endpoint: $_" -ForegroundColor Red
    }
}

# Main flow
Write-Host "Starting Odoo Docker cleanup helper" -ForegroundColor Green
if ($CallAppDrop) { Call-AppDropAll -port $Port }

$containers = List-Containers
$volumes = List-Volumes
$networks = List-Networks

if (-not $containers -and -not $volumes -and -not $networks) {
    Write-Host "Nothing to remove. Exiting." -ForegroundColor Green
    exit 0
}

if (-not $Force) {
    Write-Host "\nPreview complete. Press Enter to proceed with removals, or Ctrl+C to cancel." -ForegroundColor Yellow
    Read-Host | Out-Null
}

# Remove containers
if ($containers) {
    Write-Host "\nRemoving containers..." -ForegroundColor Yellow
    $containers | ForEach-Object {
        $cid = ($_ -split "\t")[0]
        try {
            docker rm -f $cid | Write-Host
        } catch {
            Write-Host "Failed to remove container $cid: $_" -ForegroundColor Red
        }
    }
}

# Remove volumes
if ($volumes) {
    Write-Host "\nRemoving volumes..." -ForegroundColor Yellow
    $volumes | ForEach-Object {
        try {
            docker volume rm $_ | Write-Host
        } catch {
            Write-Host "Failed to remove volume $_: $_" -ForegroundColor Red
        }
    }
}

# Remove networks
if ($networks) {
    Write-Host "\nRemoving networks..." -ForegroundColor Yellow
    $networks | ForEach-Object {
        $id = ($_ -split '\s+')[0]
        try {
            docker network rm $id | Write-Host
        } catch {
            Write-Host "Failed to remove network $id: $_" -ForegroundColor Red
        }
    }
}

Write-Host "\nCleanup complete." -ForegroundColor Green
