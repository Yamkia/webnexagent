from odoo import models, fields

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
