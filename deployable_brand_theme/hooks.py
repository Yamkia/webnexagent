from odoo import api, SUPERUSER_ID

def post_init_hook(cr, registry):
    """Assign a default brand to existing websites after module install."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    Brand = env['deployable.brand']
    Website = env['website']
    if not Brand.search([], limit=1):
        default_brand = Brand.create({
            'name': 'GreenMotive',
            'code': 'greenmotive',
            'primary_color': '#34D399',
            'secondary_color': '#0f766e',
            'logo_svg': '/deployable_brand_theme/static/src/img/logo.svg'
        })
        for website in Website.search([]):
            website.brand_id = default_brand.id
