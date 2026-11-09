# Copyright 2026 DevsCodeSpace (https://devscodespace.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
{
    'name': 'Advanced Menu Management',
    'version': '19.0.1.0.0',
    'summary': 'Hide or show Odoo menus globally, per user, company or '
               'security group, and let users hide the menus they do not use.',
    'description': """
Advanced Menu Management
========================
Centralised, auditable menu visibility for Odoo 19:

* Interactive menu tree with search, filters and a per-user preview
* Hide menus globally, for users, companies or security groups
* "Show only for" restrictions for users, companies and groups
* Personal menu preferences ("Hide Menus Through Preferences")
* Never grants access: it only narrows Odoo's standard menu visibility
""",
    'author': 'DevsCodeSpace',
    'maintainer': 'DevsCodeSpace',
    'website': 'https://devscodespace.com',
    'category': 'Administration/Technical',
    'license': 'LGPL-3',
    'depends': ['web'],
    'data': [
        'security/dcs_menu_management_security.xml',
        'security/ir.model.access.csv',
        'data/dcs_menu_management_data.xml',
        'views/dcs_menu_rule_views.xml',
        'views/ir_ui_menu_views.xml',
        'views/res_users_views.xml',
        'wizard/dcs_menu_personal_wizard_views.xml',
        'views/dcs_menu_management_menus.xml',
    ],
    'demo': [
        'demo/dcs_menu_management_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'dcs_menu_management/static/src/menu_tree/*',
            'dcs_menu_management/static/src/user_menu/*',
        ],
        'web.assets_tests': [
            'dcs_menu_management/static/tests/tours/*',
        ],
    },
    'images': [
        'static/description/banner.png',
        'static/description/main_screenshot.png',
    ],
    'application': True,
    'installable': True,
    'uninstall_hook': '_dcs_uninstall_hook',
}
