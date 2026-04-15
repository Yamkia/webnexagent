{
    "name": "Zisanda Hub",
    "version": "1.0.0",
    "summary": "Zisanda Hub theme for Odoo website and backend branding.",
    "category": "Theme/Website",
    "author": "Your Company",
    "license": "LGPL-3",
    "application": False,
    "depends": ["web", "website"],
    "data": [
        "views/assets.xml",
        "views/brand_views.xml",
        "security/ir.model.access.csv",
    ],
    "assets": {
        "web.assets_backend": [
            "white_label/static/src/scss/brand.scss",
        ],
        "web.assets_frontend": [
            "white_label/static/src/scss/brand.scss",
        ],
    },
    "installable": True,
    "auto_install": False,
}
