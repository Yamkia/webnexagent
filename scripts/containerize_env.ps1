<#
containerize_env.ps1
Usage: .\containerize_env.ps1 -Name mysite [-Version 19.0] [-ImageTag webnex/mysite:19.0] [-Registry ghcr.io/myorg]
#>
param(
  [Parameter(Mandatory=$true)][string]$Name,
  [string]$Version = '19.0',
  [string]$ImageTag = '',
  [string]$Registry = '',
  [string]$Mode = ''
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projRoot = Resolve-Path "$scriptDir\.."
$envMode = $Mode
if (-not $envMode) { $envMode = $env:APP_ENV }
if (-not $envMode) { $envMode = 'development' }

if (-not $ImageTag) { $ImageTag = "webnex/odoo-$Name:$Version-$envMode" }
if ($Registry) {
  $namePart = $ImageTag.Split('/')[-1]
  $ImageTag = "$Registry/$namePart"
}

# choose build context
$buildCtx = Join-Path $projRoot 'docker\odoo-19-provision'
if ($Version -like '18*') { $buildCtx = Join-Path $projRoot 'docker\odoo-18-provision' }

Write-Host "Building image $ImageTag from $buildCtx"
docker build -t $ImageTag $buildCtx

$envDir = Join-Path $projRoot "environments\$Name"
New-Item -ItemType Directory -Path $envDir -Force | Out-Null
$composePath = Join-Path $envDir 'docker-compose.yml'

 $compose = @"
version: '3.8'

services:
  odoo-$Name:
    image: $ImageTag
    # Prefer using an env_file to pick up .env.development/.env.staging/.env.production
    env_file: ../../.env.$envMode
    environment:
      POSTGRES_HOST: db
      POSTGRES_USER: \\${POSTGRES_USER:-odoo}
      POSTGRES_PASSWORD: \\${POSTGRES_PASSWORD:-odoo}
    ports:
      - "8069:8069"
    volumes:
      - ../../addons:/mnt/extra-addons
      - ../../deployable_brand_theme:/mnt/brand_theme
      - odoo_${Name}_data:/var/lib/odoo
    depends_on:
      - db

volumes:
  odoo_${Name}_data:
"@

Set-Content -Path $composePath -Value $compose -Encoding UTF8
Write-Host "Wrote $composePath"
Write-Host "Run: docker compose -f $composePath up -d"
if ($Registry) { Write-Host "Push image: docker push $ImageTag" }
