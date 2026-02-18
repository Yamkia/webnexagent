from odoo import models, fields


class WebnexSample(models.Model):
    _name = 'webnex.sample'
    _description = 'WebNex Sample'

    name = fields.Char(string='Name', required=True)
