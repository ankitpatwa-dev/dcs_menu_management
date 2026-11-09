# Copyright 2026 DevsCodeSpace (https://devscodespace.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, UserError

from .dcs_menu_rule import MANAGER_GROUPS

PERSONAL_FIELD = 'dcs_personal_hidden_menu_ids'
FAVORITE_FIELD = 'dcs_favorite_menu_ids'
ALLOW_FIELD = 'dcs_allow_menu_preferences'
FAVORITES_FLAG = 'dcs_show_favorites'
RECENT_FLAG = 'dcs_show_recent'
FLAG_FIELDS = (ALLOW_FIELD, FAVORITES_FLAG, RECENT_FLAG)
CACHE_FIELDS = (ALLOW_FIELD, PERSONAL_FIELD, FAVORITE_FIELD, FAVORITES_FLAG, RECENT_FLAG)
# Only "link", "unlink", "clear" and "set" are accepted on the menu lists:
# a user must never create, update or delete menu records through them.
SAFE_COMMANDS = (Command.UNLINK, Command.LINK, Command.CLEAR, Command.SET)


class ResUsers(models.Model):
    _inherit = 'res.users'

    dcs_allow_menu_preferences = fields.Boolean(
        string='Hide Menus Through Preferences',
        help='Allow this user to hide the menus they do not use and to reorder '
             'their applications. Only menu administrators can change this option.')
    dcs_personal_hidden_menu_ids = fields.Many2many(
        'ir.ui.menu', 'dcs_user_personal_hidden_menu_rel', 'user_id', 'menu_id',
        string='My Hidden Menus', user_writeable=True,
        help='Menus hidden for this user only. Remove a menu from the list to '
             'show it again (reload the page to apply).')
    dcs_show_favorites = fields.Boolean(
        string='Favorite Menus',
        help='Show the star in the top bar with this user\'s favorite menus. '
             'The user can add the menu they are on and remove favorites.')
    dcs_favorite_menu_ids = fields.Many2many(
        'ir.ui.menu', 'dcs_user_favorite_menu_rel', 'user_id', 'menu_id',
        string='Favorites', user_writeable=True,
        help='Shortcuts shown under the star in the top bar. Menus the user '
             'cannot see are never shown.')
    dcs_show_recent = fields.Boolean(
        string='Recent Menus',
        help='Show the history icon in the top bar with the menus this user '
             'opened most recently.')
    dcs_hidden_menu_ids = fields.Many2many(
        'ir.ui.menu', string='Hidden Menus',
        compute='_compute_dcs_hidden_menu_ids', inverse='_inverse_dcs_hidden_menu_ids',
        groups=MANAGER_GROUPS, context={'ir.ui.menu.full_list': True},
        help='Menus hidden for this user by an administrator. Stored as "Hide for '
             'Users" on each menu\'s visibility rule, so it also appears in Menu '
             'Configuration.')
    dcs_app_order_count = fields.Integer(
        compute='_compute_dcs_app_order_count', groups=MANAGER_GROUPS)

    # Odoo 20: users update their own record through the standard "self user
    # write access" rule. Only the two menu lists are user_writeable; write()
    # below additionally requires the matching option, the user's own record and
    # safe many2many commands. Options are not user_writeable and write() limits
    # them to menu administrators.

    # ------------------------------------------------------------------
    # Administrator-hidden menus (backed by dcs.menu.rule)
    # ------------------------------------------------------------------
    def _compute_dcs_hidden_menu_ids(self):
        Rule = self.env['dcs.menu.rule'].with_context(active_test=False)
        rules = Rule.search([('hide_user_ids', 'in', self.ids)]) if self.ids else Rule
        for user in self:
            user.dcs_hidden_menu_ids = rules.filtered(
                lambda r: user in r.hide_user_ids and r.active).menu_id

    def _inverse_dcs_hidden_menu_ids(self):
        if not self.env.user._dcs_is_menu_manager():
            raise AccessError(_('Only menu administrators can hide menus for users.'))
        Rule = self.env['dcs.menu.rule'].with_context(active_test=False)
        for user in self:
            wanted = user.dcs_hidden_menu_ids
            current = Rule.search([('hide_user_ids', 'in', user.id)])
            for rule in current.filtered(lambda r: r.menu_id not in wanted):
                rule.hide_user_ids = [Command.unlink(user.id)]
            for menu in wanted - current.menu_id:
                rule = menu._dcs_get_or_create_rule()
                rule.write({'hide_user_ids': [Command.link(user.id)], 'active': True})

    def _compute_dcs_app_order_count(self):
        data = self.env['dcs.menu.sequence']._read_group(
            [('user_id', 'in', self.ids)], ['user_id'], ['__count'])
        counts = {user.id: count for user, count in data}
        for user in self:
            user.dcs_app_order_count = counts.get(user.id, 0)

    # ------------------------------------------------------------------
    # Guards
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
                raise UserError(_('Menu lists can only add or remove menus.'))

    def _dcs_check_menu_values(self, vals):
        if self.env.su:
            return
        current = self.env.user
        is_manager = current._dcs_is_menu_manager()
        if any(flag in vals for flag in FLAG_FIELDS) and not is_manager:
            raise AccessError(_('Only menu administrators can change menu options of users.'))
        for field_name, flag, message in (
            (PERSONAL_FIELD, ALLOW_FIELD,
             _('You are not allowed to hide menus through your preferences.')),
            (FAVORITE_FIELD, FAVORITES_FLAG,
             _('Favorite menus are not enabled for you.')),
        ):
            if field_name not in vals:
                continue
            self._dcs_validate_menu_commands(vals[field_name])
            for user in self:
                if user == current:
                    if not (user.sudo()[flag] or is_manager):
                        raise AccessError(message)
                elif not is_manager:
                    raise AccessError(_('You cannot change the menus of another user.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if self.env.su:
                continue
            if any(vals.get(f) for f in CACHE_FIELDS):
                if not self.env.user._dcs_is_menu_manager():
                    raise AccessError(_('Only menu administrators can set menu '
                                        'options on users.'))
                self._dcs_validate_menu_commands(vals.get(PERSONAL_FIELD))
                self._dcs_validate_menu_commands(vals.get(FAVORITE_FIELD))
        return super().create(vals_list)

    def write(self, vals):
        self._dcs_check_menu_values(vals)
        res = super().write(vals)
        if any(f in vals for f in CACHE_FIELDS):
            self.env.transaction.invalidate_ormcache('default')
        return res

    # ------------------------------------------------------------------
    # Actions
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

    def action_dcs_open_app_order(self):
        """Application order of this user (administrators, or the user
        themself when allowed to customise their menus)."""
        self.ensure_one()
        current = self.env.user
        if not current._dcs_is_menu_manager() and not (
                self == current and current.sudo().dcs_allow_menu_preferences):
            raise AccessError(_('You are not allowed to change this application order.'))
        return self.env['dcs.menu.order.wizard']._dcs_action(self)

    def action_dcs_copy_menu_settings(self):
        """Administrators: copy this user's menu settings to other users."""
        self.ensure_one()
        if not self.env.user._dcs_is_menu_manager():
            raise AccessError(_('Only menu administrators can copy menu settings.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Copy Menu Settings'),
            'res_model': 'dcs.menu.copy.wizard',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {'default_source_user_id': self.id},
        }

    def action_dcs_reset_personal_menus(self):
        """Administrators: clear the personal hidden menus of these users."""
        if not self.env.user._dcs_is_menu_manager():
            raise AccessError(_('Only menu administrators can reset personal menus.'))
        self.write({PERSONAL_FIELD: [Command.clear()]})
        return True
