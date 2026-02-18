{
    "name": "GreenMotive White Label Theme",
    "version": "1.1.3",
    "summary": "Multi-brand white-label theme: switch UI per environment or website.",
    "category": "Theme/Website",
    "author": "Your Company",
    "license": "LGPL-3",
    "application": True,
    "depends": ["web", "website"],
    "assets": {
        "web.assets_backend": [
            "deployable_brand_theme/static/src/css/backend_theme.css",
            "deployable_brand_theme/static/src/css/modern_dashboard.css",
        ],
        "web.assets_frontend": [
            "deployable_brand_theme/static/src/css/hero_landing.css",
            "deployable_brand_theme/static/src/css/website_brand.css",
        ],
    },
    "data": [
        "views/assets.xml",
        "security/ir.model.access.csv",
        "data/brand_data.xml",
        "views/brand_views.xml",
        "views/brand_dashboard.xml",
        "views/brand_preview.xml",
        "data/website_data.xml",
    ],
    "qweb": [
        "views/hero_landing.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "auto_install": False
}