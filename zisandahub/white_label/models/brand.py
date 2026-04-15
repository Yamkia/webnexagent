from odoo import models, fields, api


class WhiteLabelBrand(models.Model):
    _name = 'white.label'
    _description = 'White Label Brand'
    _order = 'name'

    name = fields.Char(required=True)
    code = fields.Char(required=True, help='Short code used for asset class and website assignment.')
    primary_color = fields.Char(default='#0d6efd')
    secondary_color = fields.Char(default='#6610f')
    logo_svg = fields.Char(help='Path or URL to SVG logo asset.')
    favicon = fields.Binary(help='Optional favicon image.')
    is_active = fields.Boolean(default=True)

    website_ids = fields.One2many('website', 'brand_id', string='Websites')

    def action_preview_brand(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/brand/preview/{self.id}',
            'target': 'new',
        }

    @api.model
    def apply_theme(self, website_id=None):
        websites = self.env['website'].browse(website_id) if website_id else self.env['website'].search([])
        for w in websites:
            if self and self.code:
                w.write({'brand_id': self.id})
        return True
