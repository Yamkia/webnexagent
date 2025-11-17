{
    "name": "GreenMotive White Label Theme",
    "version": "1.1.0",
    "summary": "Multi-brand white-label theme: switch UI per environment or website.",
    "category": "Theme/Website",
    "author": "Your Company",
    "license": "LGPL-3",
    "depends": ["web"],
    "assets": {
        "web.assets_backend": [
            "deployable_brand_theme/static/src/css/backend_theme.css",
        ],
    },
    "data": [
        "security/ir.model.access.csv",
        "views/force_theme.xml",
        "data/brand_data.xml",
        "data/website_data.xml",
        "views/brand_views.xml",
        "views/brand_dashboard.xml",
        "views/brand_preview.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "auto_install": False
}