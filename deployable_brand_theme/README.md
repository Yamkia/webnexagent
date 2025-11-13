# Multi-Brand White Label Theme for OdooGreenMotive White-Label Theme

=============================

A comprehensive Odoo addon for white-labeling your Odoo environment with multiple brand templates. Each environment can have its own custom UI/UX, colors, logos, and styling—perfect for multi-tenant SaaS deployments or agency workflows.

This is a minimal Odoo theme module scaffold you can customize and install on an Odoo Community instance.

---

Structure

## 🎨 Features- __manifest__.py - module metadata

- views/assets.xml - includes SCSS and JS into website.assets_frontend

✅ **Multiple Brand Templates** – Define unlimited brands with unique colors, logos, and styles  - views/layout.xml - QWeb template that replaces the site header

✅ **Dynamic CSS Variables** – Colors and theming tokens injected at runtime per brand  - data/website_data.xml - sample company/website defaults

✅ **Per-Website Brand Assignment** – Assign different brands to different websites in multi-site setups  - static/src/scss/brand.scss - SCSS you should edit for colors and spacing

✅ **SCSS Architecture** – Maintainable brand-scoped styles with CSS custom properties  - static/src/js/brand.js - small JS helpers

✅ **Admin UI** – Manage brands via Odoo backend (Website → Configuration → Brands)  - static/src/img/logo.svg - placeholder logo

✅ **Automated Provisioning** – Script to apply brands during environment creation or CI/CD  

✅ **Environment Variable Support** – Select brand via `ODOO_BRAND_CODE` for deployment automation  How to use (quick):

1. Copy this folder into your Odoo `addons` or into an `extra-addons` directory that Odoo knows about.

---2. Restart Odoo and update the app list (Apps > Update Apps List).

3. Install "GreenMotive White Label Theme" from Apps.

## 📦 Installation

Runtime mount option (recommended for per-request branding):

### 1. Install the module- If you want the environment creation flow to include this module on-the-fly, clone/copy this folder into the `extra_addons` dir that you mount into the Odoo container, and include it in `--addons-path`.



Copy this directory to your Odoo addons path:Customization tips

- Edit `static/src/scss/brand.scss` to change colors, radiuses and layout.

```bash- Override more QWeb templates by adding XML files under `views/` and listing them in `__manifest__.py`.

cp -r deployable_brand_theme /path/to/odoo/addons/- Avoid direct DB ID changes; use XML ids and external IDs where possible.

```

Rollback/Uninstall

### 2. Update module list- Theme modules are uninstallable via Apps > Installed Modules.

- Before installing a theme in production, take a DB snapshot (pg_dump) so you can restore if necessary.

```bash

./odoo-bin -c odoo.conf -u all -d your_databaseIf you'd like, I can:

```- Generate multiple theme variants automatically (light/dark) in this scaffold.

- Integrate runtime cloning of a git repo and mounting into the environment creation flow in `app.py`.

Or via UI: **Apps → Update Apps List**- Add a UI input to your planner so users can supply a git repo URL for branding.


### 3. Install the addon

Search for "GreenMotive White Label Theme" and click **Install**.

---

## 🚀 Quick Start

### Create a New Brand

1. Go to **Website → Configuration → Brands**
2. Click **Create**
3. Fill in:
   - **Name**: Display name (e.g., "TechPro")
   - **Code**: Short identifier (e.g., `techpro`)
   - **Primary Color**: Main brand color (hex)
   - **Secondary Color**: Accent color (hex)
   - **Logo SVG**: Path to logo asset

### Assign Brand to Website

**Option A: Via UI**
1. Go to **Website → Configuration → Settings**
2. Select your website
3. Under **Branding**, choose the brand from dropdown
4. Save

**Option B: Via Provisioning Script**

```bash
python provision_brand.py --brand-code techpro --db-name production_db
```

---

## 🏗️ Architecture Overview

### Brand Model (`deployable.brand`)

```python
class DeployableBrand(models.Model):
    _name = 'deployable.brand'
    
    name = fields.Char(required=True)          # "TechPro"
    code = fields.Char(required=True)          # "techpro"
    primary_color = fields.Char()              # "#3B82F6"
    secondary_color = fields.Char()            # "#1E40AF"
    logo_svg = fields.Char()                   # "/path/to/logo.svg"
    favicon = fields.Binary()
    website_ids = fields.One2many('website', 'brand_id')
```

### Website Extension

```python
class Website(models.Model):
    _inherit = 'website'
    
    brand_id = fields.Many2one('deployable.brand', string='Brand')
```

### Dynamic Template Rendering

The `body` element gets a brand-specific class:

```html
<body class="brand-techpro" data-brand="techpro">
```

CSS variables are injected into `:root`:

```css
:root {
  --brand-primary: #3B82F6;
  --brand-secondary: #1E40AF;
}
```

### SCSS Structure

```
static/src/scss/
├── brand.scss              # Main brand styles with CSS custom properties
├── brands/
│   ├── _greenmotive.scss   # (Optional) GreenMotive-specific overrides
│   ├── _techpro.scss       # (Optional) TechPro-specific overrides
│   └── _luxe.scss          # (Optional) LuxeBrand-specific overrides
```

**Key Pattern:**
- Use `var(--brand-primary)` in styles instead of hardcoded colors
- Brand-specific body classes (`.brand-techpro`) for scoped overrides
- SCSS variables for compile-time defaults

---

## 🎯 Usage Patterns

### Pattern 1: Multi-Tenant SaaS

Each customer gets their own database with a brand:

```bash
# Production tenant
python provision_brand.py --brand-code acmecorp --db-name acmecorp_prod

# Staging tenant
python provision_brand.py --brand-code acmecorp --db-name acmecorp_staging
```

### Pattern 2: Multi-Site Single Database

One database, multiple websites with different brands:

```bash
python provision_brand.py --brand-code greenmotive --website-domain www.greenmotive.com
python provision_brand.py --brand-code techpro --website-domain www.techpro.io
```

### Pattern 3: Environment-Based Auto-Selection

Set `ODOO_BRAND_CODE` environment variable:

```bash
export ODOO_BRAND_CODE=luxe
./odoo-bin -c odoo.conf
```

The post-install hook will auto-assign the brand.

---

## 🔧 Advanced Customization

### Adding a New Brand

**1. Create brand record in `data/brand_data.xml`:**

```xml
<record id="brand_newbrand" model="deployable.brand">
  <field name="name">NewBrand</field>
  <field name="code">newbrand</field>
  <field name="primary_color">#FF5733</field>
  <field name="secondary_color">#C70039</field>
  <field name="logo_svg">/deployable_brand_theme/static/src/img/newbrand-logo.svg</field>
</record>
```

**2. Add brand scope to SCSS (`static/src/scss/brand.scss`):**

```scss
body.brand-newbrand {
  --brand-primary: #FF5733;
  --brand-secondary: #C70039;
  --brand-bg: #fff5f5;
}
```

**3. (Optional) Create brand-specific overrides:**

```scss
// static/src/scss/brands/_newbrand.scss
body.brand-newbrand {
  .gm-header {
    border-bottom: 2px solid var(--brand-primary);
  }
  
  .btn-brand {
    border-radius: 4px; // Square buttons for this brand
  }
}
```

### Custom Logo Per Brand

Place logos in `static/src/img/` and reference in brand record:

```
static/src/img/
├── logo.svg              # Default
├── techpro-logo.svg
├── luxe-logo.svg
└── newbrand-logo.svg
```

### Dark Mode Support

Extend CSS variables:

```scss
body.brand-techpro {
  --brand-primary: #3B82F6;
  --brand-secondary: #1E40AF;
  
  @media (prefers-color-scheme: dark) {
    --brand-primary: #60A5FA;
    --brand-bg: #1a1a1a;
    --brand-text: #f7f7f7;
  }
}
```

---

## 🤖 Environment Provisioning

### CI/CD Integration

**GitLab CI Example:**

```yaml
deploy_staging:
  script:
    - ./odoo-bin -c odoo.conf -d staging_db -i deployable_brand_theme --stop-after-init
    - python deployable_brand_theme/provision_brand.py --brand-code techpro --db-name staging_db
    - ./odoo-bin -c odoo.conf -d staging_db
```

**Docker Compose Example:**

```yaml
services:
  web:
    environment:
      - ODOO_BRAND_CODE=greenmotive
      - ODOO_DB=production
    command: >
      bash -c "
        ./odoo-bin -i deployable_brand_theme --stop-after-init &&
        python /mnt/extra-addons/deployable_brand_theme/provision_brand.py --brand-code $$ODOO_BRAND_CODE &&
        ./odoo-bin
      "
```

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ODOO_BRAND_CODE` | Brand code to auto-assign | `techpro` |
| `ODOO_URL` | Odoo instance URL | `http://localhost:8069` |
| `ODOO_DB` | Database name | `production_db` |
| `ODOO_USER` | Admin username | `admin` |
| `ODOO_PASSWORD` | Admin password | `admin` |

---

## 📁 File Structure

```
deployable_brand_theme/
├── __init__.py
├── __manifest__.py
├── hooks.py                          # Post-install hook
├── provision_brand.py                # Provisioning script
├── README.md                         # This file
├── models/
│   ├── __init__.py
│   ├── brand.py                      # Brand model
│   ├── website.py                    # Website extension
│   └── res_config_settings.py       # Settings integration
├── views/
│   ├── assets.xml                    # Asset bundles
│   ├── layout.xml                    # Header/layout templates
│   ├── brand_templates.xml          # Brand class injection
│   ├── brand_views.xml              # Admin views for brands
│   └── res_config_settings_view.xml # Website settings
├── data/
│   ├── website_data.xml             # Default website data
│   └── brand_data.xml               # Example brand records
├── security/
│   └── ir.model.access.csv          # Access rights
└── static/
    └── src/
        ├── scss/
        │   └── brand.scss            # Main brand styles
        ├── js/
        │   └── brand.js              # Frontend JS
        └── img/
            ├── logo.svg
            ├── techpro-logo.svg
            └── luxe-logo.svg
```

---

## 🧪 Testing

### Manual Test

1. Install module
2. Create two brands (Brand A, Brand B)
3. Create two websites
4. Assign Brand A to Website 1, Brand B to Website 2
5. Visit each website and verify:
   - Correct logo displayed
   - Correct colors applied
   - Body has correct `.brand-<code>` class

### Automated Test (Future)

```python
# tests/test_brand.py
def test_brand_assignment(self):
    brand = self.env['deployable.brand'].create({
        'name': 'Test Brand',
        'code': 'testbrand',
        'primary_color': '#FF0000'
    })
    website = self.env['website'].search([], limit=1)
    website.brand_id = brand
    self.assertEqual(website._get_brand_code(), 'testbrand')
```

---

## 🔐 Security

- Brand management requires `website.group_website_designer` permission
- Users can view brands (read-only)
- Only website designers/admins can create/edit brands

See `security/ir.model.access.csv` for details.

---

## 🚧 Roadmap / Next Steps

- [ ] **Asset versioning** – Cache busting for CSS/JS
- [ ] **Brand preview** – Live preview panel in admin UI
- [ ] **Component library** – Pre-built branded snippets (cards, buttons, forms)
- [ ] **Multi-language support** – Brand names/metadata per locale
- [ ] **Advanced theming** – Typography scales, spacing tokens
- [ ] **REST API** – `/api/brands` endpoint for external integrations
- [ ] **Brand templates** – Export/import brand configs as JSON

---

## 📝 License

LGPL-3 (same as Odoo)

---

## 💬 Support

For issues or feature requests, contact [Your Company] or open an issue in the repository.

---

**Happy White-Labeling! 🎨**
