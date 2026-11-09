# Copyright 2026 DevsCodeSpace (https://devscodespace.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

MANAGER_GROUPS = 'base.group_system,dcs_menu_management.group_menu_manager'

FULL_LIST_CTX = {'ir.ui.menu.full_list': True}


class DcsMenuRule(models.Model):
    """Visibility restrictions for one menu.

    A rule can only *remove* a menu from what Odoo would normally show. It
    never makes a menu visible to someone who could not see it without this
    module (see ``ir.ui.menu._dcs_evaluate``).
    """
    _name = 'dcs.menu.rule'
    _description = 'Menu Visibility Rule'
    _rec_name = 'menu_id'
    _order = 'menu_complete_name, id'

    menu_id = fields.Many2one(
        'ir.ui.menu', string='Menu', required=True, ondelete='cascade',
        index=True, context=FULL_LIST_CTX,
        help='Menu restricted by this rule. Restrictions also apply to all '
             'of its sub-menus.')
    active = fields.Boolean(
        default=True,
        help='Archive the rule to suspend its restrictions without losing '
             'the configuration.')
    menu_complete_name = fields.Char(
        string='Menu Path', related='menu_id.complete_name', store=True)
    menu_xml_id = fields.Char(
        string='External ID', compute='_compute_menu_info')
    menu_action_info = fields.Char(
        string='Action', compute='_compute_menu_info')
    menu_active = fields.Boolean(
        string='Menu Active', related='menu_id.active')
    menu_group_ids = fields.Many2many(
        'res.groups', string='Odoo Standard Groups',
        related='menu_id.group_ids', readonly=True,
        help='Groups defined on the menu by Odoo or by the module that '
             'created it. This module never changes them.')

    hide_globally = fields.Boolean(
        string='Hide for Everyone',
        help='Hide this menu and its sub-menus for every user.')

    hide_user_ids = fields.Many2many(
        'res.users', 'dcs_menu_rule_hide_user_rel', 'rule_id', 'user_id',
        string='Hide for Users', domain=[('share', '=', False)],
        help='These users never see the menu.')
    show_user_ids = fields.Many2many(
        'res.users', 'dcs_menu_rule_show_user_rel', 'rule_id', 'user_id',
        string='Show Only for Users', domain=[('share', '=', False)],
        help='When set, only these users can see the menu (provided Odoo '
             'already lets them see it).')

    hide_company_ids = fields.Many2many(
        'res.company', 'dcs_menu_rule_hide_company_rel', 'rule_id',
        'company_id', string='Hide for Companies',
        help='The menu is hidden when every active company of the user is in '
             'this list.')
    show_company_ids = fields.Many2many(
        'res.company', 'dcs_menu_rule_show_company_rel', 'rule_id',
        'company_id', string='Show Only for Companies',
        help='When set, the menu is shown only if at least one active company '
             'of the user is in this list.')

    show_group_ids = fields.Many2many(
        'res.groups', 'dcs_menu_rule_show_group_rel', 'rule_id', 'group_id',
        string='Show Only for Groups',
        help='When set, only members of at least one of these groups see the '
             'menu. Combined with the menu\'s own Odoo groups, never instead '
             'of them.')
    hide_group_ids = fields.Many2many(
        'res.groups', 'dcs_menu_rule_hide_group_rel', 'rule_id', 'group_id',
        string='Hide for Groups',
        help='Members of any of these groups do not see the menu.')

    note = fields.Text(string='Internal Note')

    summary = fields.Char(compute='_compute_summary', string='Restrictions')
    restriction_count = fields.Integer(compute='_compute_summary')
    is_protected = fields.Boolean(
        compute='_compute_is_protected',
        help='Settings and Menu Management menus are never hidden for menu '
             'administrators, so they cannot lock themselves out.')
    personal_user_ids = fields.Many2many(
        'res.users', string='Hidden Personally By',
        compute='_compute_personal_user_ids',
        help='Users who hid this menu through their own preferences.')

    _menu_unique = models.Constraint(
        'unique(menu_id)',
        'A visibility rule already exists for this menu. Edit or unarchive '
        'the existing rule instead.',
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends('menu_id')
    def _compute_menu_info(self):
        menus = self.menu_id
        xmlids = menus._get_menuitems_xmlids() if menus else {}
        infos = menus._dcs_action_labels() if menus else {}
        for rule in self:
            rule.menu_xml_id = xmlids.get(rule.menu_id.id, False)
            rule.menu_action_info = infos.get(rule.menu_id.id, False)

    @api.depends('hide_globally', 'hide_user_ids', 'show_user_ids',
                 'hide_company_ids', 'show_company_ids', 'show_group_ids',
                 'hide_group_ids', 'active')
    def _compute_summary(self):
        for rule in self:
            parts = []
            if rule.hide_globally:
                parts.append(_('Hidden for everyone'))
            if rule.hide_user_ids:
                parts.append(_('Hidden for %s user(s)', len(rule.hide_user_ids)))
            if rule.show_user_ids:
                parts.append(_('Only %s user(s)', len(rule.show_user_ids)))
            if rule.hide_company_ids:
                parts.append(_('Hidden for %s company(ies)', len(rule.hide_company_ids)))
            if rule.show_company_ids:
                parts.append(_('Only %s company(ies)', len(rule.show_company_ids)))
            if rule.show_group_ids:
                parts.append(_('Only %s group(s)', len(rule.show_group_ids)))
            if rule.hide_group_ids:
                parts.append(_('Hidden for %s group(s)', len(rule.hide_group_ids)))
            rule.restriction_count = len(parts)
            rule.summary = ' · '.join(parts) if parts else _('No restriction')

    @api.depends('menu_id')
    def _compute_is_protected(self):
        protected = self.env['ir.ui.menu']._dcs_protected_menu_ids()
        for rule in self:
            rule.is_protected = rule.menu_id.id in protected

    @api.depends('menu_id')
    def _compute_personal_user_ids(self):
        Users = self.env['res.users'].with_context(active_test=False)
        users = Users.search([('dcs_personal_hidden_menu_ids', 'in', self.menu_id.ids)])
        for rule in self:
            rule.personal_user_ids = users.filtered(
                lambda u: rule.menu_id in u.dcs_personal_hidden_menu_ids)

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('hide_user_ids', 'show_user_ids', 'hide_company_ids',
                    'show_company_ids', 'hide_group_ids', 'show_group_ids')
    def _check_consistency(self):
        for rule in self:
            for hide, show, label in (
                (rule.hide_user_ids, rule.show_user_ids, _('users')),
                (rule.hide_company_ids, rule.show_company_ids, _('companies')),
                (rule.hide_group_ids, rule.show_group_ids, _('groups')),
            ):
                both = hide & show
                if both:
                    raise ValidationError(_(
                        'Menu "%(menu)s": the same %(kind)s cannot be in both the '
                        '"Hide for" and the "Show only for" lists (%(names)s).',
                        menu=rule.menu_id.complete_name, kind=label,
                        names=', '.join(both.mapped('display_name'))))
            if rule.hide_user_ids.filtered('share') or rule.show_user_ids.filtered('share'):
                raise ValidationError(_(
                    'Menu rules apply to internal users only; portal and public '
                    'users never see backend menus.'))

    @api.constrains('hide_company_ids', 'show_company_ids')
    def _check_companies_allowed(self):
        if self.env.su:
            return
        allowed = set(self.env.user._get_company_ids())
        for rule in self:
            foreign = (rule.hide_company_ids | rule.show_company_ids).filtered(
                lambda c: c.id not in allowed)
            if foreign:
                raise ValidationError(_(
                    'You can only use companies you have access to in menu '
                    'rules (%s).', ', '.join(foreign.mapped('name'))))

    # ------------------------------------------------------------------
    # CRUD: every change invalidates the cached menu trees
    # ------------------------------------------------------------------
    def _dcs_check_manager(self):
        if not self.env.su and not self.env.user._dcs_is_menu_manager():
            raise AccessError(_('Only menu administrators can change menu '
                                'visibility rules.'))

    @api.model_create_multi
    def create(self, vals_list):
        self._dcs_check_manager()
        rules = super().create(vals_list)
        self.env.transaction.invalidate_ormcache('default')
        return rules

    def write(self, vals):
        self._dcs_check_manager()
        res = super().write(vals)
        self.env.transaction.invalidate_ormcache('default')
        return res

    def unlink(self):
        self._dcs_check_manager()
        res = super().unlink()
        self.env.transaction.invalidate_ormcache('default')
        return res

    def copy(self, default=None):
        raise ValidationError(_('A menu can only have one visibility rule.'))

    # ------------------------------------------------------------------
    # Cached snapshot used by the visibility engine
    # ------------------------------------------------------------------
    @api.model
    def _dcs_rules_snapshot(self):
        """Immutable data of every active rule, shared by all users.

        Cached in the registry; any rule change clears it. Read as superuser
        because it is evaluated for every user, and the result never leaves
        the server except as the user's own menu tree.
        """
        return self.env['ir.ui.menu']._dcs_rules_snapshot_cached()

    def action_open_menu_tree(self):
        return self.env['ir.actions.actions']._for_xml_id(
            'dcs_menu_management.action_dcs_menu_tree')
