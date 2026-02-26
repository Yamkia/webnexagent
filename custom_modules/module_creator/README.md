# Module Creator

This addon provides a simple wizard to scaffold new Odoo modules into the `custom_modules` folder.

Usage:

- Install this addon (`Module Creator`) from Apps (update Apps list if needed).
- Open the menu `Module Creator / Create Module`, fill the form and press Create.
- A new folder will be created under the repository `custom_modules/<module_name>` with basic files.

Notes:

- The wizard only writes files; you must update the Odoo addons list and install the generated module manually.
- Adjust the `custom_modules` path logic in `wizards/create_module_wizard.py` if your Odoo server runs with a different working directory.
