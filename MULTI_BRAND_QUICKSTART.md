# 🎨 Multi-Brand White Label Odoo - Ready to Deploy!

## ✅ What You Have Now

Your Odoo instance now supports **multiple brand templates** with unique UI/UX for each environment. Perfect for:

- 🏢 **Multi-tenant SaaS** - Each customer gets their own branded environment
- 🌐 **Multi-site deployments** - Different brands per website
- 🎯 **White-label solutions** - Agency/reseller branded installations
- 🚀 **Environment-based branding** - Dev/Staging/Prod with different themes

---

## 📦 Quick Start (5 minutes)

### 1. Install the Module

**Option A: Via Odoo UI**
```
1. Restart Odoo
2. Apps → Update Apps List
3. Search "GreenMotive White Label Theme"
4. Click Install
```

**Option B: Via Command Line**
```bash
cd deployable_brand_theme
python quickstart.py --demo
```

### 2. View Pre-Configured Brands

Navigate to: **Website → Configuration → Brands**

You'll see 3 example brands:
- 🟢 **GreenMotive** - Emerald green eco-friendly theme
- 🔵 **TechPro** - Corporate blue professional theme  
- 🟣 **LuxeBrand** - Premium purple luxury theme

### 3. Apply a Brand

**Via UI:**
1. Go to **Website → Configuration → Settings**
2. Under "Branding", select a brand
3. Save & refresh your website

**Via CLI:**
```bash
python provision_brand.py --brand-code greenmotive --db-name your_database
```

### 4. Preview Before Applying

1. Go to **Website → Configuration → Brands**
2. Click any brand → Click **"Preview Brand"** button
3. See live preview with component showcase

---

## 🎨 Create Your Own Brand

### Quick Method (UI Only)

1. **Website → Configuration → Brands → Create**
2. Fill in:
   - Name: "AcmeCorp"
   - Code: "acme" (lowercase, no spaces)
   - Primary Color: `#FF5733`
   - Secondary Color: `#C70039`
   - Logo SVG: `/path/to/logo.svg`
3. Add SCSS (see below)
4. Assign to website

### Add Brand Styles

Edit `deployable_brand_theme/static/src/scss/brand.scss`:

```scss
body.brand-acme {
  --brand-primary: #FF5733;
  --brand-secondary: #C70039;
  --brand-bg: #fff5f5;
}
```

Restart Odoo → Update module → Done!

---

## 🚀 Deployment Options

### Docker (Recommended)

```bash
# Single brand environment
export ODOO_BRAND_CODE=greenmotive
docker-compose -f docker-compose.brand.yml up -d
```

### Kubernetes

```bash
kubectl apply -f k8s/deployment.yaml
kubectl exec deployment/odoo -- \
  python3 /mnt/extra-addons/deployable_brand_theme/provision_brand.py \
  --brand-code greenmotive
```

### Traditional Server

```bash
# 1. Copy addon to Odoo addons path
cp -r deployable_brand_theme /opt/odoo/addons/

# 2. Restart Odoo
systemctl restart odoo

# 3. Install & provision
./odoo-bin -d production -i deployable_brand_theme --stop-after-init
python provision_brand.py --brand-code mybrand --db-name production
```

---

## 📚 Documentation

| File | Description |
|------|-------------|
| `deployable_brand_theme/README.md` | Complete user guide with examples |
| `deployable_brand_theme/STYLING_GUIDE.md` | SCSS patterns, dark mode, performance |
| `deployable_brand_theme/DEPLOYMENT.md` | CI/CD pipelines (GitHub, GitLab, Jenkins) |
| `deployable_brand_theme/IMPLEMENTATION_SUMMARY.md` | Technical architecture overview |

---

## 🎯 Common Use Cases

### Use Case 1: Agency White-Labeling

Deploy separate branded instances for each client:

```bash
# Client A
python provision_brand.py --brand-code client-a --db-name client_a_prod

# Client B  
python provision_brand.py --brand-code client-b --db-name client_b_prod
```

### Use Case 2: Multi-Site Portal

Multiple brands on one database:

```bash
python provision_brand.py --brand-code retail --website-domain shop.example.com
python provision_brand.py --brand-code wholesale --website-domain b2b.example.com
```

### Use Case 3: Environment-Based Branding

```bash
# Staging
export ODOO_BRAND_CODE=staging-brand
./start-odoo.sh

# Production
export ODOO_BRAND_CODE=production-brand
./start-odoo.sh
```

---

## 🔧 Customization Examples

### Dark Mode Support

```scss
body.brand-techpro {
  --brand-primary: #3B82F6;
  
  @media (prefers-color-scheme: dark) {
    --brand-primary: #60A5FA;
    --brand-bg: #1a1a1a;
    --brand-text: #f7f7f7;
  }
}
```

### Custom Components

```scss
.btn-brand {
  background: linear-gradient(135deg, 
    var(--brand-primary), 
    var(--brand-secondary)
  );
  color: white;
  border-radius: 999px;
  padding: 0.5rem 1.5rem;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  }
}
```

### Brand-Specific Layouts

```scss
body.brand-luxe {
  // Glassmorphism for luxury brand
  .card {
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(168, 85, 247, 0.1);
  }
}
```

---

## 🤖 CI/CD Integration

### GitHub Actions

```yaml
- name: Deploy Brand
  env:
    BRAND_CODE: ${{ secrets.BRAND_CODE }}
  run: |
    python provision_brand.py --brand-code $BRAND_CODE
```

### GitLab CI

```yaml
deploy:
  variables:
    BRAND_CODE: greenmotive
  script:
    - python provision_brand.py --brand-code $BRAND_CODE
```

See `deployable_brand_theme/DEPLOYMENT.md` for complete pipeline examples.

---

## 🎓 Learn More

### Interactive Wizard

```bash
cd deployable_brand_theme
python quickstart.py --demo
```

### Run Demo

```bash
# See all sample brands
python quickstart.py --list

# Get code snippets for new brands
python quickstart.py --create-brands
```

---

## ✨ Key Features

✅ **Unlimited Brands** - Create as many as you need  
✅ **Dynamic CSS** - Colors injected at runtime  
✅ **Visual Admin** - Kanban dashboard with previews  
✅ **API Endpoints** - JSON API for external tools  
✅ **Automation Ready** - CLI + environment variables  
✅ **Docker/K8s** - Production deployment guides  
✅ **Dark Mode** - Built-in support  
✅ **Performance** - Asset optimization included  

---

## 🆘 Troubleshooting

**Q: Brand not showing after install?**
```bash
# Clear cache and update
./odoo-bin -d your_db -u deployable_brand_theme --stop-after-init
```

**Q: CSS not applying?**
```bash
# Check body class in browser
# Should be: <body class="brand-yourcode">
# If not, restart Odoo
```

**Q: Preview button not working?**
```bash
# Ensure controllers are loaded
# Check logs for import errors
```

**Q: How to add more brands?**
- See section "Create Your Own Brand" above
- Or check `deployable_brand_theme/README.md`

---

## 📊 Architecture Overview

```
Request → Odoo
  ↓
Website Context (brand_id)
  ↓
Template: <body class="brand-{code}">
  ↓
CSS Variables: --brand-primary, --brand-secondary
  ↓
SCSS: Scoped styles apply
  ↓
Logo/Name: Dynamically rendered
```

---

## 🎉 You're Ready!

Your Odoo instance now supports professional multi-brand white-labeling. Deploy with confidence using:

1. ✅ Pre-built brand models & UI
2. ✅ Dynamic theming system  
3. ✅ Automation scripts
4. ✅ Docker/K8s manifests
5. ✅ CI/CD pipeline examples
6. ✅ Comprehensive documentation

**Next Steps:**
1. Create your first brand via UI
2. Customize colors & logo
3. Preview before applying
4. Deploy to production

For detailed guides, see files in `deployable_brand_theme/` folder.

---

**Happy White-Labeling! 🚀**

*Questions? Check `deployable_brand_theme/README.md` or run `python quickstart.py --demo`*
