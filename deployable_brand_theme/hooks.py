from odoo import api, SUPERUSER_ID

def post_init_hook(env):
    """Create a default brand after module install (Odoo 19+ env signature)."""
    if not isinstance(env, api.Environment):
        env = api.Environment(env.cr, SUPERUSER_ID, {})

    Brand = env["deployable.brand"]
    WebsitePage = env["website.page"]

    # Get or create default brand
    default_brand = Brand.search([("code", "=", "greenmotive")], limit=1)
    if not default_brand:
        Brand.create(
            {
                "name": "GreenMotive",
                "code": "greenmotive",
                "primary_color": "#34D399",
                "secondary_color": "#0f766e",
                "logo_svg": "/deployable_brand_theme/static/src/img/logo.svg",
            }
        )

    # Ensure hero landing page exists and is linked to the template
    try:
        template = env.ref("deployable_brand_theme.hero_landing_page")
        WebsitePage.search([("url", "=", "/nexus-hero")], limit=1).unlink()
        WebsitePage.create(
            {
                "name": "Nexus Hero Landing",
                "url": "/nexus-hero",
                "type": "qweb",
                "view_id": template.id,
            }
        )
    except Exception:
        # If template is missing for any reason, skip silently to not block install
        pass

    # Apply theme templates to all websites and set theme_id (best-effort)
    try:
        mod = env['ir.module.module'].search([('name', '=', 'deployable_brand_theme')], limit=1)
        if mod:
            websites = env['website'].search([])
            for w in websites:
                try:
                    mod._theme_load(w)
                    w.write({'theme_id': mod.id})
                except Exception:
                    # non-fatal; continue
                    pass
    except Exception:
        # ensure post-init hook never fails the installation
        pass
