import os
from odoo import api, fields, models


class CreateModuleWizard(models.TransientModel):
    _name = 'create.module.wizard'
    _description = 'Create a new module scaffold'

    name = fields.Char(string='Module Title', required=True)
    module_name = fields.Char(string='Module Technical Name', required=True)
    author = fields.Char(string='Author', default='Your Company')
    license = fields.Selection(
        [('LGPL-3', 'LGPL-3'), ('AGPL-3', 'AGPL-3'), ('Other', 'Other')],
        string='License', default='LGPL-3')
    short_description = fields.Text(string='Short Description')

    def action_create_module(self):
        self.ensure_one()
        # Determine custom_modules directory relative to this addon
        # file is in: <repo>/custom_modules/module_creator/wizards/
        # base -> <repo>/custom_modules
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        custom_modules_dir = base
        target = os.path.join(custom_modules_dir, self.module_name)

        if not os.path.exists(custom_modules_dir):
            os.makedirs(custom_modules_dir)

        if os.path.exists(target):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Module exists',
                    'message': 'A module with that technical name already exists.',
                    'sticky': False,
                }
            }

        os.makedirs(os.path.join(target, 'models'))
        os.makedirs(os.path.join(target, 'views'))
        os.makedirs(os.path.join(target, 'security'))

        # __init__.py
        with open(os.path.join(target, '__init__.py'), 'w', encoding='utf-8') as f:
            f.write("from . import models\n")

        # manifest
        manifest = {
            'name': self.name,
            'version': '19.0.1.0.0',
            'author': self.author,
            'license': self.license,
            'category': 'Uncategorized',
            'summary': self.short_description or '',
            'depends': ['base'],
            'data': [],
            'installable': True,
            'application': False,
        }
        with open(os.path.join(target, '__manifest__.py'), 'w', encoding='utf-8') as f:
            f.write(repr(manifest))

        # models/__init__.py
        with open(os.path.join(target, 'models', '__init__.py'), 'w', encoding='utf-8') as f:
            f.write('from . import models\n')

        # models/models.py (example model)
        with open(os.path.join(target, 'models', 'models.py'), 'w', encoding='utf-8') as f:
            f.write("from odoo import models, fields\n\n")
            f.write("class ExampleModel(models.Model):\n")
            f.write("    _name = '%s.example'\n" % self.module_name)
            f.write("    _description = 'Example model for %s'\n\n" % self.module_name)
            f.write("    name = fields.Char('Name')\n")

        # simple security file
        with open(os.path.join(target, 'security', 'ir.model.access.csv'), 'w', encoding='utf-8') as f:
            f.write('id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink\n')
            f.write('access_%s_example,access_%s_example,model_%s_example,,1,1,1,1\n' % (self.module_name, self.module_name, self.module_name))

        # simple view placeholder
        with open(os.path.join(target, 'views', '%s_menu.xml' % self.module_name), 'w', encoding='utf-8') as f:
            f.write("<odoo>\n")
            f.write("  <menuitem id=\"menu_%s_root\" name=\"%s\"/>\n" % (self.module_name, self.name))
            f.write("</odoo>\n")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Module created',
                'message': 'Module scaffold created at %s' % target,
                'sticky': False,
            }
        }
