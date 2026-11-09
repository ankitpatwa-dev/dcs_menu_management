# Copyright 2026 DevsCodeSpace (https://devscodespace.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
{
    'name': 'Advanced Menu Management',
    'version': '18.0.1.1.0',
    'summary': 'Hide any menu (globally, per user, company or group), change the '
               'application order, favorite and recent menus, personal menus.',
    'description': """
Advanced Menu Management
========================
Centralised, auditable menu visibility for Odoo 18:

* Interactive menu tree with search, filters and a per-user preview
* Hide menus globally, for users, companies or security groups
* "Show only for" restrictions for users, companies and groups
* Personal menu preferences ("Hide Menus Through Preferences")
* Application order for everyone or per user
* Favorite menus (star in the top bar) and recent menus (history in the top bar)
* Copy menu settings from one user to others
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
        'wizard/dcs_menu_order_wizard_views.xml',
        'wizard/dcs_menu_copy_wizard_views.xml',
        'views/dcs_menu_management_menus.xml',
    ],
    'demo': [
        'demo/dcs_menu_management_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'dcs_menu_management/static/src/menu_tree/*',
            'dcs_menu_management/static/src/user_menu/*',
            'dcs_menu_management/static/src/shortcuts/*',
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
