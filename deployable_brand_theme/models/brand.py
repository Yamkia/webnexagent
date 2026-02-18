from odoo import models, fields, api

class DeployableBrand(models.Model):
    _name = 'deployable.brand'
    _description = 'Deployable Brand / White Label Profile'
    _order = 'name'

    name = fields.Char(required=True)
    code = fields.Char(required=True, help='Short code used for env variable mapping and asset keying.')
    primary_color = fields.Char(default='#0066ff')
    secondary_color = fields.Char(default='#003366')
    logo_svg = fields.Char(help='Path or URL to SVG logo asset.')
    favicon = fields.Binary(help='Optional favicon image.')
    is_active = fields.Boolean(default=True)

    website_ids = fields.One2many('website', 'brand_id', string='Websites')

    def action_preview_brand(self):
        """Open brand preview in new window."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/brand/preview/{self.id}',
            'target': 'new',
        }

    @api.model
    def apply_theme(self, website_id=None):
        """Public helper to apply this module's theme to one or all websites.
        Can be called remotely via XML-RPC (models.execute_kw) by our env-creator.
        """
        Module = self.env['ir.module.module'].search([('name', '=', 'deployable_brand_theme')], limit=1)
        websites = self.env['website'].browse(website_id) if website_id else self.env['website'].search([])
        if Module:
            for w in websites:
                try:
                    Module._theme_load(w)
                    w.write({'theme_id': Module.id})
                except Exception:
                    # best-effort only
                    pass
        return True
