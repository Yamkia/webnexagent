{
    "name": "GreenMotive White Label Theme",
    "version": "1.1.0",
    "summary": "Multi-brand white-label theme: switch UI per environment or website.",
    "category": "Theme/Website",
    "author": "Your Company",
    "license": "LGPL-3",
    "depends": ["website", "web"],
    "data": [
        "security/ir.model.access.csv",
        "data/website_data.xml",
        "data/brand_data.xml",
        "views/assets.xml",
        "views/layout.xml",
        "views/brand_templates.xml",
        "views/brand_views.xml",
        "views/brand_dashboard.xml",
        "views/brand_preview.xml",
        "views/res_config_settings_view.xml"
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "auto_install": False
}