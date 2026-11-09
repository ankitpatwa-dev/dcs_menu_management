# Copyright 2026 DevsCodeSpace (https://devscodespace.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class DcsMenuSequence(models.Model):
    """Order of the applications (top-level menus) in the menu bar and home menu.

    Rows without user define the order for everyone; rows of a user override it
    for that user. Odoo's own ``ir.ui.menu.sequence`` is never changed.
    """
    _name = 'dcs.menu.sequence'
    _description = 'Application Order'
    _order = 'user_id, sequence, id'

    menu_id = fields.Many2one(
        'ir.ui.menu', string='Application', required=True, ondelete='cascade',
        index=True, domain=[('parent_id', '=', False)],
        context={'ir.ui.menu.full_list': True})
    user_id = fields.Many2one(
        'res.users', string='User', ondelete='cascade', index=True,
        help='Empty: order used by everyone who has no personal order.')
    sequence = fields.Integer(default=10)

    @api.constrains('menu_id', 'user_id')
    def _check_unique(self):
        for row in self:
            if row.menu_id.parent_id:
                raise ValidationError(_('Only applications (top-level menus) can be ordered.'))
            if self.search_count([('menu_id', '=', row.menu_id.id),
                                  ('user_id', '=', row.user_id.id),
                                  ('id', '!=', row.id)]):
                raise ValidationError(_('"%s" is already ordered for this scope.',
                                        row.menu_id.name))

    def _dcs_check_scope(self, vals_list=None):
        """Global order: menu administrators. Personal order: the user, if
        allowed to hide menus through preferences, or a menu administrator."""
        if self.env.su:
            return
        user = self.env.user
        if user._dcs_is_menu_manager():
            return
        user_ids = set(self.mapped('user_id').ids) if self else set()
        for vals in vals_list or []:
            user_ids.add(vals.get('user_id') or False)
        if self.filtered(lambda r: not r.user_id):
            user_ids.add(False)
        if user_ids - {user.id} or not user.sudo().dcs_allow_menu_preferences:
            raise AccessError(_('You are not allowed to change this application order.'))

    @api.model_create_multi
    def create(self, vals_list):
        self._dcs_check_scope(vals_list)
        rows = super().create(vals_list)
        self.env.registry.clear_cache()
        return rows

    def write(self, vals):
        self._dcs_check_scope([vals] if 'user_id' in vals else None)
        res = super().write(vals)
        self.env.registry.clear_cache()
        return res

    def unlink(self):
        self._dcs_check_scope()
        res = super().unlink()
        self.env.registry.clear_cache()
        return res

    @api.model
    def _dcs_set_order(self, menu_ids, user=None):
        """Replace the order of a scope (global when ``user`` is None)."""
        user_id = user.id if user else False
        self.search([('user_id', '=', user_id)]).unlink()
        self.create([{'menu_id': menu_id, 'user_id': user_id, 'sequence': (index + 1) * 10}
                     for index, menu_id in enumerate(menu_ids)])
