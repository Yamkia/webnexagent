from odoo import api, SUPERUSER_ID

def post_init_hook(cr, registry):
    """Create a default brand after module install."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    Brand = env['deployable.brand']
    
    # Get or create default brand
    default_brand = Brand.search([('code', '=', 'greenmotive')], limit=1)
    if not default_brand:
        default_brand = Brand.create({
            'name': 'GreenMotive',
            'code': 'greenmotive',
            'primary_color': '#34D399',
            'secondary_color': '#0f766e',
            'logo_svg': '/deployable_brand_theme/static/src/img/logo.svg'
        })
    
    cr.commit()
