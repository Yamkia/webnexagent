{
    'name': 'Module Creator',
    'version': '19.0.1.0.0',
    'summary': 'Create new Odoo module scaffolds from the UI',
    'description': 'A simple addon to scaffold new Odoo modules into the custom_modules directory via a wizard.',
    'author': 'Your Company',
    'category': 'Tools',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/module_creator_views.xml',
        'views/module_creator_wizard_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
