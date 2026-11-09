# Copyright 2026 DevsCodeSpace (https://devscodespace.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError


class DcsMenuOrderWizard(models.TransientModel):
    """Drag applications into the order they should appear in.

    Scope "global": order for everyone (menu administrators).
    Scope "user": order for one user (administrators, or the user themself when
    allowed to customise their menus).
    """
    _name = 'dcs.menu.order.wizard'
    _description = 'Application Order'

    scope = fields.Selection([('global', 'Everyone'), ('user', 'One User')],
                             required=True, default='global', readonly=True)
    user_id = fields.Many2one('res.users', readonly=True)
    line_ids = fields.One2many('dcs.menu.order.wizard.line', 'wizard_id', string='Applications')
    has_custom_order = fields.Boolean(compute='_compute_has_custom_order')

    @api.depends('scope', 'user_id')
    def _compute_has_custom_order(self):
        Sequence = self.env['dcs.menu.sequence'].sudo()
        for wizard in self:
            user_id = wizard.user_id.id if wizard.scope == 'user' else False
            wizard.has_custom_order = bool(Sequence.search_count([('user_id', '=', user_id)]))

    @api.model
    def _dcs_action(self, user=None):
        name = _('Application Order: %s', user.name) if user else _('Application Order: Everyone')
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': self._name,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {'default_scope': 'user' if user else 'global',
                        'default_user_id': user.id if user else False},
        }

    @api.model
    def _dcs_check(self, scope, user):
        current = self.env.user
        if current._dcs_is_menu_manager():
            return
        if scope == 'user' and user == current and current.sudo().dcs_allow_menu_preferences:
            return
        raise AccessError(_('You are not allowed to change this application order.'))

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        scope = res.get('scope') or self.env.context.get('default_scope') or 'global'
        user = self.env['res.users'].browse(res.get('user_id') or self.env.context.get('default_user_id'))
        if scope == 'user' and not user:
            user = self.env.user
            res['user_id'] = user.id
        self._dcs_check(scope, user)
        if 'line_ids' in fields_list:
            apps = self.env['ir.ui.menu']._dcs_ordered_apps(user=user, scope_global=scope == 'global')
            res['line_ids'] = [Command.create({'menu_id': app.id, 'sequence': (i + 1) * 10})
                               for i, app in enumerate(apps)]
        return res

    def action_apply(self):
        self.ensure_one()
        self._dcs_check(self.scope, self.user_id)
        menu_ids = self.line_ids.sorted(lambda l: (l.sequence, l.id)).menu_id.ids
        self.env['dcs.menu.sequence']._dcs_set_order(
            menu_ids, self.user_id if self.scope == 'user' else None)
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_reset(self):
        """Back to the global order (user scope) or Odoo's order (global)."""
        self.ensure_one()
        self._dcs_check(self.scope, self.user_id)
        user_id = self.user_id.id if self.scope == 'user' else False
        self.env['dcs.menu.sequence'].search([('user_id', '=', user_id)]).unlink()
        return {'type': 'ir.actions.client', 'tag': 'reload'}


class DcsMenuOrderWizardLine(models.TransientModel):
    _name = 'dcs.menu.order.wizard.line'
    _description = 'Application Order Line'
    _order = 'sequence, id'

    wizard_id = fields.Many2one('dcs.menu.order.wizard', required=True, ondelete='cascade')
    sequence = fields.Integer()
    menu_id = fields.Many2one('ir.ui.menu', string='Application', required=True, readonly=True,
                              context={'ir.ui.menu.full_list': True})
    web_icon_data = fields.Binary(related='menu_id.web_icon_data')
