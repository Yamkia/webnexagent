{
    "name": "BlueWave Theme",
    "version": "1.0.0",
    "summary": "Clean blue header and dark body for Odoo backend",
    "category": "Theme/Backend",
    "author": "Your Company",
    "license": "LGPL-3",
    "depends": ["web"],
    "data": [
        "views/assets.xml"
    ],
    "assets": {
        "web.assets_backend": [
            "bluewave_theme/static/src/css/backend_theme.css",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False
}
