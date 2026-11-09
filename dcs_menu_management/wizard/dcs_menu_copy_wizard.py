# Copyright 2026 DevsCodeSpace (https://devscodespace.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, UserError


class DcsMenuCopyWizard(models.TransientModel):
    """Copy the menu settings of one user to other users (administrators)."""
    _name = 'dcs.menu.copy.wizard'
    _description = 'Copy Menu Settings'

    source_user_id = fields.Many2one('res.users', string='Copy From', required=True,
                                     domain=[('share', '=', False)])
    user_ids = fields.Many2many('res.users', string='Copy To', required=True,
                                domain="[('share', '=', False), ('id', '!=', source_user_id)]")
    copy_hidden = fields.Boolean(string='Hidden Menus', default=True,
                                 help='Menus hidden for the user by administrators.')
    copy_personal = fields.Boolean(string='Personal Hidden Menus',
                                   help='Menus the user hid through their preferences.')
    copy_favorites = fields.Boolean(string='Favorite Menus')
    copy_app_order = fields.Boolean(string='Application Order')
    copy_options = fields.Boolean(
        string='Options',
        help='Hide Menus Through Preferences, Favorite Menus and Recent Menus switches.')

    @api.model
    def _check_manager(self):
        if not self.env.user._dcs_is_menu_manager():
            raise AccessError(_('Only menu administrators can copy menu settings.'))

    @api.model
    def default_get(self, fields_list):
        self._check_manager()
        return super().default_get(fields_list)

    def action_copy(self):
        self.ensure_one()
        self._check_manager()
        source = self.source_user_id
        targets = self.user_ids - source
        if not targets:
            raise UserError(_('Choose at least one other user to copy to.'))
        if not any((self.copy_hidden, self.copy_personal, self.copy_favorites,
                    self.copy_app_order, self.copy_options)):
            raise UserError(_('Choose what to copy.'))
        if self.copy_hidden:
            Rule = self.env['dcs.menu.rule']
            for rule in Rule.search([('hide_user_ids', 'in', source.id)]):
                rule.hide_user_ids = [Command.link(user.id) for user in targets
                                      if user not in rule.show_user_ids]
        vals = {}
        if self.copy_options:
            vals.update({flag: source[flag] for flag in (
                'dcs_allow_menu_preferences', 'dcs_show_favorites', 'dcs_show_recent')})
        if self.copy_personal:
            vals['dcs_personal_hidden_menu_ids'] = [Command.set(source.dcs_personal_hidden_menu_ids.ids)]
        if self.copy_favorites:
            vals['dcs_favorite_menu_ids'] = [Command.set(source.dcs_favorite_menu_ids.ids)]
        if vals:
            targets.write(vals)
        if self.copy_app_order:
            Sequence = self.env['dcs.menu.sequence']
            order = Sequence.search([('user_id', '=', source.id)]).sorted('sequence').menu_id.ids
            for user in targets:
                if order:
                    Sequence._dcs_set_order(order, user)
                else:
                    Sequence.search([('user_id', '=', user.id)]).unlink()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _('Menu settings of %(from_user)s copied to %(count)s user(s).',
                             from_user=source.name, count=len(targets)),
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
