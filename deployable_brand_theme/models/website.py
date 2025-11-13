from odoo import models, fields

class Website(models.Model):
    _inherit = 'website'

    brand_id = fields.Many2one('deployable.brand', string='Brand', ondelete='set null')

    def _get_brand_code(self):
        self.ensure_one()
        return (self.brand_id.code or 'default') if self.brand_id else 'default'
