from odoo import fields, models


class CssManager(models.Model):
    _name = "custom.css.manager"
    _description = "Custom CSS Manager"

    name = fields.Char(default="CSS Profile", required=True)
    notes = fields.Text(string="Notes")
    css_rules = fields.Text(string="CSS Overrides")
    active = fields.Boolean(default=True)
