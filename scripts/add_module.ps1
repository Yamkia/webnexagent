param(
    [Parameter(Mandatory = $true)][string]$ModuleName,
    [ValidateSet('17','18','19')][string]$Version = '17',
    [string]$Author = 'You',
    [string]$Description = 'A simple module',
    [switch]$Restart
)

$ErrorActionPreference = 'Stop'

function Ensure-Directory { param([string]$Path) if (-not (Test-Path $Path)) { New-Item -ItemType Directory -Path $Path | Out-Null } }

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$TargetDir = Join-Path $RepoRoot "addons\$Version\$ModuleName"
Ensure-Directory $TargetDir
Ensure-Directory (Join-Path $TargetDir 'models')

# Write basic files
$init = "from . import models`n"
Set-Content -Path (Join-Path $TargetDir '__init__.py') -Value $init -Encoding UTF8

$manifest = @"
{
    'name': '$ModuleName (v$Version)',
    'version': '$Version.0.1.0',
    'summary': '$Description',
    'description': '$Description',
    'author': '$Author',
    'category': 'Tools',
    'depends': ['base'],
    'data': [],
    'installable': True,
    'application': False,
}
"@
Set-Content -Path (Join-Path $TargetDir '__manifest__.py') -Value $manifest -Encoding UTF8

$model_init = "from . import models`n"
Set-Content -Path (Join-Path $TargetDir 'models\__init__.py') -Value $model_init -Encoding UTF8

$model_py = @"
from odoo import models, fields


class ${($ModuleName -replace '-','_')}_model(models.Model):
    _name = '${ModuleName.ToLower()}.sample'
    _description = '$Description'

    name = fields.Char(string='Name', required=True)
"@
Set-Content -Path (Join-Path $TargetDir 'models\models.py') -Value $model_py -Encoding UTF8

Write-Host "Created module at: addons/$Version/$ModuleName"

if ($Restart) {
    $svc = "odoo-$Version"
    Write-Host "Restarting Odoo service: $svc"
    try { & docker compose restart $svc } catch { & docker-compose restart $svc }
}
