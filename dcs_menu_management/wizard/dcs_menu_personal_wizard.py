# Copyright 2026 DevsCodeSpace (https://devscodespace.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError

from ..models.ir_ui_menu import CTX_SKIP_PERSONAL, FULL_LIST_CTX

MAX_LEVEL = 2  # apps, sections and their items (e.g. Sales / Orders / Quotations)


class DcsMenuPersonalWizard(models.TransientModel):
    _name = 'dcs.menu.personal.wizard'
    _description = 'My Menus'

    user_id = fields.Many2one('res.users', default=lambda self: self.env.user,
                              readonly=True, required=True)
    line_ids = fields.One2many('dcs.menu.personal.wizard.line', 'wizard_id',
                               string='Menus')
    hidden_count = fields.Integer(compute='_compute_hidden_count')

    @api.depends('line_ids.hidden')
    def _compute_hidden_count(self):
        for wizard in self:
            wizard.hidden_count = len(wizard.line_ids.filtered('hidden'))

    @api.model
    def _check_allowed(self):
        if not self.env.user.sudo().dcs_allow_menu_preferences:
            raise AccessError(_('You are not allowed to hide menus through '
                                'your preferences. Ask your administrator.'))

    @api.model
    def _available_menus(self):
        """Menus the user can see without personal preferences (levels 0-2),
        plus the ones already hidden personally."""
        Menu = self.env['ir.ui.menu']
        visible = Menu.with_context(**{CTX_SKIP_PERSONAL: True})._visible_menu_ids(
            Menu._dcs_debug())
        if self.env.user._dcs_is_menu_manager():
            visible = visible - Menu._dcs_protected_menu_ids()
        menus = Menu.with_context(**FULL_LIST_CTX).browse(sorted(visible))
        # only menus the user can actually reach: every ancestor visible
        menus = menus.filtered(
            lambda m: m.parent_path.count('/') <= MAX_LEVEL + 1
            and all(int(pid) in visible for pid in m.parent_path.strip('/').split('/')))
        hidden = self.env.user.sudo().dcs_personal_hidden_menu_ids
        return (menus | hidden.with_context(**FULL_LIST_CTX)).sorted(
            lambda m: (m.complete_name or '').lower())

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'line_ids' in fields_list:
            self._check_allowed()
            hidden_ids = set(self.env.user.sudo().dcs_personal_hidden_menu_ids.ids)
            res['line_ids'] = [Command.create({
                'sequence': index,
                'menu_id': menu.id,
                'hidden': menu.id in hidden_ids,
            }) for index, menu in enumerate(self._available_menus())]
        return res

    def action_apply(self):
        self.ensure_one()
        self._check_allowed()
        if self.user_id != self.env.user:
            raise AccessError(_('You can only manage your own menus.'))
        listed = self.line_ids.menu_id
        keep = self.env.user.sudo().dcs_personal_hidden_menu_ids - listed
        hidden = self.line_ids.filtered('hidden').menu_id | keep
        self.env.user.write({'dcs_personal_hidden_menu_ids': [Command.set(hidden.ids)]})
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_show_all(self):
        self.ensure_one()
        self.line_ids.hidden = False
        return self._reopen()

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {'dialog_size': 'large'},
        }


class DcsMenuPersonalWizardLine(models.TransientModel):
    _name = 'dcs.menu.personal.wizard.line'
    _description = 'My Menus Line'
    _order = 'sequence, id'

    wizard_id = fields.Many2one('dcs.menu.personal.wizard', required=True,
                                ondelete='cascade')
    sequence = fields.Integer()
    menu_id = fields.Many2one('ir.ui.menu', required=True, readonly=True,
                              context=FULL_LIST_CTX)
    menu_path = fields.Char(string='Menu Path', compute='_compute_menu_info')
    app_name = fields.Char(string='Application', compute='_compute_menu_info')
    level = fields.Integer(compute='_compute_menu_info')
    hidden = fields.Boolean(string='Hide')

    @api.depends('menu_id')
    def _compute_menu_info(self):
        for line in self:
            menu = line.menu_id.sudo()
            path = menu.parent_path or ''
            root_id = int(path.split('/')[0]) if path else menu.id
            line.app_name = self.env['ir.ui.menu'].sudo().browse(root_id).name
            line.menu_path = menu.complete_name
            line.level = max(path.count('/') - 1, 0)
