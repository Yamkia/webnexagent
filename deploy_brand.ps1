# Multi-Brand Odoo Deployment Script
# Usage: .\deploy_brand.ps1 -BrandCode greenmotive

param(
    [Parameter(Mandatory=$false)]
    [string]$BrandCode = "greenmotive",
    
    [Parameter(Mandatory=$false)]
    [switch]$Fresh
)

Write-Host "Deploying Odoo with Brand: $BrandCode" -ForegroundColor Green

# Set environment variable
$env:ODOO_BRAND_CODE = $BrandCode

if ($Fresh) {
    Write-Host "Cleaning up previous deployment..." -ForegroundColor Yellow
    docker-compose -f docker-compose.brand.yml down -v
}

Write-Host "Starting Docker containers..." -ForegroundColor Cyan
docker-compose -f docker-compose.brand.yml up -d

Write-Host "Waiting for Odoo to start (30 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

Write-Host "Provisioning brand: $BrandCode" -ForegroundColor Magenta
docker-compose -f docker-compose.brand.yml exec -T odoo python3 /mnt/extra-addons/deployable_brand_theme/provision_brand.py --brand-code $BrandCode --db-name odoo --odoo-url http://localhost:8069

Write-Host ""
Write-Host "Deployment complete!" -ForegroundColor Green
Write-Host "Access Odoo at: http://localhost:8069" -ForegroundColor Cyan
Write-Host "Default credentials: admin / admin" -ForegroundColor Cyan
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Yellow
Write-Host "  - View logs:    docker-compose -f docker-compose.brand.yml logs -f odoo" -ForegroundColor White
Write-Host "  - Stop:         docker-compose -f docker-compose.brand.yml down" -ForegroundColor White
Write-Host "  - Fresh start:  .\deploy_brand.ps1 -BrandCode $BrandCode -Fresh" -ForegroundColor White
