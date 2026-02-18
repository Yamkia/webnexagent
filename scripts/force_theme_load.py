import odoo
from odoo import api

DB='odoo-61ff4b42-db'
reg = odoo.modules.registry.Registry(DB)
with reg.cursor() as cr:
    env = api.Environment(cr, 1, {})
    mod = env['ir.module.module'].search([('name','=','deployable_brand_theme')])
    website = env['website'].search([], limit=1)
    print('Found mod:', bool(mod), 'website:', bool(website))
    if mod and website:
        print('Calling _theme_load')
        mod._theme_load(website)
        cr.commit()
        print('Theme load complete')
    else:
        print('Nothing to do')
