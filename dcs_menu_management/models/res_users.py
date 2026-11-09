# Copyright 2026 DevsCodeSpace (https://devscodespace.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, UserError

PERSONAL_FIELD = 'dcs_personal_hidden_menu_ids'
ALLOW_FIELD = 'dcs_allow_menu_preferences'
# Only "link", "unlink", "clear" and "set" are accepted on the personal list:
# a user must never create, update or delete menu records through it.
SAFE_COMMANDS = (Command.UNLINK, Command.LINK, Command.CLEAR, Command.SET)


class ResUsers(models.Model):
    _inherit = 'res.users'

    dcs_allow_menu_preferences = fields.Boolean(
        string='Hide Menus Through Preferences',
        help='Allow this user to hide menus they do not use from their own '
             'preferences. Only menu administrators can change this option.')
    dcs_personal_hidden_menu_ids = fields.Many2many(
        'ir.ui.menu', 'dcs_user_personal_hidden_menu_rel', 'user_id', 'menu_id',
        string='My Hidden Menus', user_writeable=True,
        help='Menus hidden for this user only. Remove a menu from the list to '
             'show it again (reload the page to apply).')

    # Odoo 20: users update their own record through the standard
    # "self user write access" rule. Only the personal list is user_writeable;
    # write() below additionally requires the permission, the user's own
    # record and safe many2many commands. The permission flag itself is not
    # user_writeable (Access Rights administrators only) and write() limits it
    # to menu administrators.

    # ------------------------------------------------------------------
    def _dcs_is_menu_manager(self):
        self.ensure_one()
        return self.has_group('base.group_system') or \
            self.has_group('dcs_menu_management.group_menu_manager')

    @api.model
    def _dcs_validate_menu_commands(self, value):
        """Reject commands that would create, change or delete menus."""
        for command in value or []:
            if isinstance(command, (list, tuple)) and command and command[0] not in SAFE_COMMANDS:
                raise UserError(_('Personal menu preferences can only add or '
                                  'remove menus from the list.'))

    def _dcs_check_menu_values(self, vals):
        if self.env.su:
            return
        current = self.env.user
        is_manager = current._dcs_is_menu_manager()
        if ALLOW_FIELD in vals and not is_manager:
            raise AccessError(_('Only menu administrators can allow users to '
                                'hide menus through their preferences.'))
        if PERSONAL_FIELD in vals:
            self._dcs_validate_menu_commands(vals[PERSONAL_FIELD])
            for user in self:
                if user == current:
                    if not (user.sudo().dcs_allow_menu_preferences or is_manager):
                        raise AccessError(_('You are not allowed to hide menus '
                                            'through your preferences.'))
                elif not is_manager:
                    raise AccessError(_('You cannot change the menu preferences '
                                        'of another user.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not self.env.su and (vals.get(ALLOW_FIELD) or vals.get(PERSONAL_FIELD)):
                if not self.env.user._dcs_is_menu_manager():
                    raise AccessError(_('Only menu administrators can set menu '
                                        'preferences on users.'))
                self._dcs_validate_menu_commands(vals.get(PERSONAL_FIELD))
        return super().create(vals_list)

    def write(self, vals):
        self._dcs_check_menu_values(vals)
        res = super().write(vals)
        if ALLOW_FIELD in vals or PERSONAL_FIELD in vals:
            self.env.transaction.invalidate_ormcache('default')
        return res

    # ------------------------------------------------------------------
    def action_dcs_open_personal_menus(self):
        """Open the "My Menus" wizard for the current user."""
        self.ensure_one()
        if self != self.env.user:
            raise AccessError(_('You can only manage your own menus.'))
        if not self.sudo().dcs_allow_menu_preferences:
            raise AccessError(_('You are not allowed to hide menus through '
                                'your preferences. Ask your administrator.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('My Menus'),
            'res_model': 'dcs.menu.personal.wizard',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {'dialog_size': 'large'},
        }

    def action_dcs_reset_personal_menus(self):
        """Administrators: clear the personal hidden menus of these users."""
        if not self.env.user._dcs_is_menu_manager():
            raise AccessError(_('Only menu administrators can reset personal menus.'))
        self.write({PERSONAL_FIELD: [Command.clear()]})
        return True
