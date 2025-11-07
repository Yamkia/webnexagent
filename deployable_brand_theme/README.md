GreenMotive White-Label Theme
=============================

This is a minimal Odoo theme module scaffold you can customize and install on an Odoo Community instance.

Structure
- __manifest__.py - module metadata
- views/assets.xml - includes SCSS and JS into website.assets_frontend
- views/layout.xml - QWeb template that replaces the site header
- data/website_data.xml - sample company/website defaults
- static/src/scss/brand.scss - SCSS you should edit for colors and spacing
- static/src/js/brand.js - small JS helpers
- static/src/img/logo.svg - placeholder logo

How to use (quick):
1. Copy this folder into your Odoo `addons` or into an `extra-addons` directory that Odoo knows about.
2. Restart Odoo and update the app list (Apps > Update Apps List).
3. Install "GreenMotive White Label Theme" from Apps.

Runtime mount option (recommended for per-request branding):
- If you want the environment creation flow to include this module on-the-fly, clone/copy this folder into the `extra_addons` dir that you mount into the Odoo container, and include it in `--addons-path`.

Customization tips
- Edit `static/src/scss/brand.scss` to change colors, radiuses and layout.
- Override more QWeb templates by adding XML files under `views/` and listing them in `__manifest__.py`.
- Avoid direct DB ID changes; use XML ids and external IDs where possible.

Rollback/Uninstall
- Theme modules are uninstallable via Apps > Installed Modules.
- Before installing a theme in production, take a DB snapshot (pg_dump) so you can restore if necessary.

If you'd like, I can:
- Generate multiple theme variants automatically (light/dark) in this scaffold.
- Integrate runtime cloning of a git repo and mounting into the environment creation flow in `app.py`.
- Add a UI input to your planner so users can supply a git repo URL for branding.
