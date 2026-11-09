# Copyright 2026 DevsCodeSpace (https://devscodespace.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import fields, models

DEFAULT_RECENT_LIMIT = 10


class DcsMenuRecent(models.Model):
    """Menus recently opened by a user (one row per user and menu).

    Record rules restrict every user, administrators included, to their own rows.
    """
    _name = 'dcs.menu.recent'
    _description = 'Recently Opened Menu'
    _order = 'visit_date desc, id desc'

    user_id = fields.Many2one('res.users', required=True, ondelete='cascade', index=True,
                              default=lambda self: self.env.user)
    menu_id = fields.Many2one('ir.ui.menu', required=True, ondelete='cascade',
                              context={'ir.ui.menu.full_list': True})
    visit_date = fields.Datetime(required=True, default=fields.Datetime.now)

    _sql_constraints = [
        ('user_menu_unique', 'unique(user_id, menu_id)', 'A menu is listed once per user.'),
    ]
