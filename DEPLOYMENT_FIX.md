# Brand Theme Deployment Guide

## 🐛 Problem Fixed

The issue was that the custom module theme wasn't being applied when creating new environments. This was due to:

1. **Load order**: `brand_data.xml` needed to load BEFORE `website_data.xml`
2. **Post-install hook**: Wasn't properly assigning brands to websites
3. **Docker provisioning**: Provision script was running before Odoo was ready

## ✅ Solutions Applied

### 1. Updated `__manifest__.py`
- Reordered data files so brands load first
- Ensures brand records exist before websites try to reference them

### 2. Fixed `hooks.py`
- Improved post-install hook to search for brands by code
- Assigns default brand to ALL websites without a brand
- Added `cr.commit()` for persistence

### 3. Updated `website_data.xml`
- Explicitly assigns GreenMotive brand to default website
- Ensures immediate brand assignment on install

### 4. Fixed `docker-compose.brand.yml`
- Removed premature provision script call
- Module installation now happens cleanly during startup

## 🚀 Quick Start

### Option 1: Docker Deployment (Recommended)

```powershell
# Deploy with default GreenMotive brand
.\deploy_brand.ps1

# Deploy with specific brand
.\deploy_brand.ps1 -BrandCode techpro

# Fresh deployment (removes old data)
.\deploy_brand.ps1 -BrandCode greenmotive -Fresh
```

### Option 2: Manual Docker

```powershell
# Set brand code
$env:ODOO_BRAND_CODE = "greenmotive"

# Start containers
docker-compose -f docker-compose.brand.yml up -d

# Wait for Odoo to start (about 30 seconds)
Start-Sleep -Seconds 30

# Provision the brand
docker-compose -f docker-compose.brand.yml exec odoo python3 /mnt/extra-addons/deployable_brand_theme/provision_brand.py --brand-code greenmotive --db-name odoo --odoo-url http://localhost:8069
```

### Option 3: Local Development (without Docker)

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Navigate to Odoo source
cd odoo-source

# Install/upgrade the module
python odoo-bin -c ../odoo.conf -d your_db_name -i deployable_brand_theme --stop-after-init

# Start Odoo
python odoo-bin -c ../odoo.conf -d your_db_name
```

## 🔍 Verify Installation

After deployment, check if the theme is applied:

1. **Access Odoo**: http://localhost:8069
2. **Login**: admin / admin (default)
3. **Navigate to**: Website → Configuration → Brands
4. **Verify**: You should see 3 brands (GreenMotive, TechPro, LuxeBrand)
5. **Check website**: Go to Website → Configuration → Settings
   - Under "Branding" section, verify a brand is selected
6. **View frontend**: Visit the website homepage
   - Check that the header shows the correct brand name
   - Verify colors match the brand's primary/secondary colors

## 🎨 Available Brands

| Brand | Code | Primary Color | Secondary Color |
|-------|------|---------------|-----------------|
| GreenMotive | greenmotive | #34D399 | #0f766e |
| TechPro | techpro | #3B82F6 | #1E40AF |
| LuxeBrand | luxe | #A855F7 | #6B21A8 |

## 🛠️ Troubleshooting

### Brand not showing after install

```powershell
# Stop containers
docker-compose -f docker-compose.brand.yml down

# Start fresh
docker-compose -f docker-compose.brand.yml up -d

# Wait and check logs
docker-compose -f docker-compose.brand.yml logs -f odoo
```

### Manual brand assignment

```powershell
# Connect to Odoo container
docker-compose -f docker-compose.brand.yml exec odoo bash

# Run provision script
python3 /mnt/extra-addons/deployable_brand_theme/provision_brand.py \
  --brand-code greenmotive \
  --db-name odoo \
  --odoo-url http://localhost:8069
```

### Check if module is installed

```powershell
# View Odoo logs
docker-compose -f docker-compose.brand.yml logs odoo | Select-String "deployable_brand_theme"
```

## 📝 Creating New Brands

### Step 1: Add brand data

Edit `deployable_brand_theme/data/brand_data.xml`:

```xml
<record id="brand_mybrand" model="deployable.brand">
  <field name="name">MyBrand</field>
  <field name="code">mybrand</field>
  <field name="primary_color">#FF0000</field>
  <field name="secondary_color">#990000</field>
  <field name="logo_svg">/deployable_brand_theme/static/src/img/mybrand-logo.svg</field>
  <field name="is_active" eval="True"/>
</record>
```

### Step 2: Add brand styles

Edit `deployable_brand_theme/static/src/scss/brand.scss`:

```scss
body.brand-mybrand {
  --brand-primary: #FF0000;
  --brand-secondary: #990000;
  --brand-bg: #fff5f5;
}
```

### Step 3: Restart and update

```powershell
# Restart containers
docker-compose -f docker-compose.brand.yml restart odoo

# Update module
docker-compose -f docker-compose.brand.yml exec odoo odoo -c /etc/odoo/odoo.conf -d odoo -u deployable_brand_theme --stop-after-init

# Restart again
docker-compose -f docker-compose.brand.yml restart odoo
```

## 🔗 Related Documentation

- [Full README](deployable_brand_theme/README.md)
- [Styling Guide](deployable_brand_theme/STYLING_GUIDE.md)
- [Multi-Brand Quickstart](MULTI_BRAND_QUICKSTART.md)
- [Architecture](deployable_brand_theme/IMPLEMENTATION_SUMMARY.md)

## ✅ Checklist

After deployment, verify:

- [ ] Docker containers are running
- [ ] Can access Odoo at http://localhost:8069
- [ ] Module "GreenMotive White Label Theme" is installed
- [ ] Brands visible in Website → Configuration → Brands
- [ ] Default website has a brand assigned
- [ ] Website homepage shows correct brand styling
- [ ] Header displays brand logo and name

## 🎉 Success!

Your custom brand theme should now be properly applied to new environments!
