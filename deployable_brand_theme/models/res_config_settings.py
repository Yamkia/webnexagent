from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    website_brand_id = fields.Many2one(related='website_id.brand_id',
                                       readonly=False,
                                       string='Brand')
