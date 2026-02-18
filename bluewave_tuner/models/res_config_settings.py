from odoo import api, fields, models


class BluewaveThemeSettings(models.TransientModel):
    _inherit = "res.config.settings"

    bw_header = fields.Char(string="Header color", default="#111c3d")
    bw_header_border = fields.Char(string="Header border", default="#0b1329")
    bw_bg = fields.Char(string="Background", default="#0b1326")
    bw_panel = fields.Char(string="Panel", default="#0f1f46")
    bw_text = fields.Char(string="Text", default="#e9f1ff")
    bw_muted = fields.Char(string="Muted text", default="#aab7d4")
    bw_accent = fields.Char(string="Accent", default="#4a7bff")
    bw_border_opacity = fields.Float(string="Border opacity (0-1)", default=0.06)

    @api.model
    def get_values(self):
        res = super().get_values()
        ICP = self.env["ir.config_parameter"].sudo()
        res.update(
            bw_header=ICP.get_param("bluewave_tuner.bw_header", "#111c3d"),
            bw_header_border=ICP.get_param("bluewave_tuner.bw_header_border", "#0b1329"),
            bw_bg=ICP.get_param("bluewave_tuner.bw_bg", "#0b1326"),
            bw_panel=ICP.get_param("bluewave_tuner.bw_panel", "#0f1f46"),
            bw_text=ICP.get_param("bluewave_tuner.bw_text", "#e9f1ff"),
            bw_muted=ICP.get_param("bluewave_tuner.bw_muted", "#aab7d4"),
            bw_accent=ICP.get_param("bluewave_tuner.bw_accent", "#4a7bff"),
            bw_border_opacity=float(ICP.get_param("bluewave_tuner.bw_border_opacity", 0.06)),
        )
        return res

    def set_values(self):
        super().set_values()
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("bluewave_tuner.bw_header", self.bw_header or "#111c3d")
        ICP.set_param("bluewave_tuner.bw_header_border", self.bw_header_border or "#0b1329")
        ICP.set_param("bluewave_tuner.bw_bg", self.bw_bg or "#0b1326")
        ICP.set_param("bluewave_tuner.bw_panel", self.bw_panel or "#0f1f46")
        ICP.set_param("bluewave_tuner.bw_text", self.bw_text or "#e9f1ff")
        ICP.set_param("bluewave_tuner.bw_muted", self.bw_muted or "#aab7d4")
        ICP.set_param("bluewave_tuner.bw_accent", self.bw_accent or "#4a7bff")
        ICP.set_param("bluewave_tuner.bw_border_opacity", self.bw_border_opacity or 0.06)
