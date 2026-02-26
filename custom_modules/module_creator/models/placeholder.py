from odoo import models


class ModuleCreatorPlaceholder(models.Model):
    _name = 'module.creator.placeholder'
    _description = 'Placeholder model for module_creator'

    # This addon primarily uses a wizard; keep a tiny model for potential ACLs
    pass
