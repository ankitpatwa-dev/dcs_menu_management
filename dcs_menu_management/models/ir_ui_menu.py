# Copyright 2026 DevsCodeSpace (https://devscodespace.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
"""Menu visibility engine.

Odoo computes the menus a user may see in ``ir.ui.menu._visible_menu_ids``
(menu groups + read access on the action's model, cached per set of groups).
Every menu entry point uses it: ``search`` on menus, ``get_user_roots``,
``load_menus`` (web client, command palette, home menu) and
``load_menus_root``.

This module wraps that method and only ever *removes* ids from Odoo's result,
so it cannot grant visibility. Evaluation order (all conditions must allow the
menu; the first one that hides it is reported as the reason):

1. Odoo standard visibility (menu groups, model access, debug-only menus)
2. Protected menus: Settings and Menu Management stay visible for menu
   administrators, whatever the rules say
3. Hide for everyone
4. Hide for users / Show only for users
5. Hide for companies / Show only for companies (active companies)
6. Show only for groups / Hide for groups
7. Personal preferences of the user (if allowed)
8. Hierarchy: a hidden menu hides all of its sub-menus; a menu without
   action whose sub-menus are all hidden is hidden as well

Company rules depend on the companies active in the web client. Odoo caches
``load_menus`` per user only, so that method evaluates company rules against
*all* the user's companies (a menu stays if at least one of them allows it);
the exact active companies are applied afterwards by the uncached web client
entry points (see ``load_web_menus``). Context keys used internally can be sent
by any client, so none of them can switch a restriction off.
"""

from collections import defaultdict

from odoo import SUPERUSER_ID, _, _lt, api, fields, models, tools
from odoo.exceptions import AccessError
from odoo.http import request

from .dcs_menu_rule import MANAGER_GROUPS

FULL_LIST_CTX = {'ir.ui.menu.full_list': True}

# context keys used internally
CTX_SKIP_COMPANY = 'dcs_menu_skip_company'
CTX_SKIP_PERSONAL = 'dcs_menu_skip_personal'

PROTECTED_XMLIDS = (
    'base.menu_administration',
)
MODULE = 'dcs_menu_management'

REASONS = {
    'standard': _lt('Odoo groups or access rights'),
    'global': _lt('Hidden for everyone'),
    'user_hidden': _lt('Hidden for this user'),
    'user_not_allowed': _lt('User not in "Show only"'),
    'company_hidden': _lt('Hidden for the company'),
    'company_not_allowed': _lt('Company not in "Show only"'),
    'group_not_allowed': _lt('Group not in "Show only"'),
    'group_hidden': _lt('Hidden for a group'),
    'personal': _lt('Personal preference'),
    'parent': _lt('Parent menu hidden'),
    'empty': _lt('All sub-menus hidden'),
}
COMPANY_REASONS = ('company_hidden', 'company_not_allowed')


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    dcs_rule_ids = fields.One2many(
        'dcs.menu.rule', 'menu_id', string='Visibility Rules',
        groups=MANAGER_GROUPS, context={'active_test': False})
    dcs_rule_id = fields.Many2one(
        'dcs.menu.rule', string='Visibility Rule',
        compute='_compute_dcs_rule', groups=MANAGER_GROUPS)
    dcs_visibility_state = fields.Selection(
        [('default', 'Odoo Default'),
         ('restricted', 'Restricted'),
         ('hidden', 'Hidden'),
         ('suspended', 'Rule Archived')],
        string='Visibility', compute='_compute_dcs_rule',
        search='_search_dcs_visibility_state', groups=MANAGER_GROUPS)
    dcs_rule_summary = fields.Char(
        string='Restrictions', compute='_compute_dcs_rule',
        groups=MANAGER_GROUPS)
    dcs_xml_id = fields.Char(
        string='External ID', compute='_compute_dcs_xml_id',
        search='_search_dcs_xml_id', groups=MANAGER_GROUPS)
    dcs_action_info = fields.Char(
        string='Action Details', compute='_compute_dcs_action_info',
        groups=MANAGER_GROUPS)
    dcs_child_count = fields.Integer(
        string='Sub-menus', compute='_compute_dcs_child_count',
        groups=MANAGER_GROUPS)

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------
    @api.depends('dcs_rule_ids', 'dcs_rule_ids.active',
                 'dcs_rule_ids.hide_globally', 'dcs_rule_ids.summary')
    def _compute_dcs_rule(self):
        for menu in self:
            rule = menu.dcs_rule_ids[:1]
            menu.dcs_rule_id = rule
            if not rule or not rule.restriction_count:
                state = 'default'
            elif not rule.active:
                state = 'suspended'
            elif rule.hide_globally:
                state = 'hidden'
            else:
                state = 'restricted'
            menu.dcs_visibility_state = state
            menu.dcs_rule_summary = rule.summary if rule and rule.restriction_count else False

    def _search_dcs_visibility_state(self, operator, value):
        if operator not in ('=', '!=', 'in', 'not in'):
            raise NotImplementedError(_('Unsupported search on visibility.'))
        values = [value] if isinstance(value, str) else list(value or [])
        Rule = self.env['dcs.menu.rule'].with_context(active_test=False)
        rules = Rule.search([])
        ids_by_state = defaultdict(list)
        for rule in rules:
            if not rule.restriction_count:
                continue
            if not rule.active:
                ids_by_state['suspended'].append(rule.menu_id.id)
            elif rule.hide_globally:
                ids_by_state['hidden'].append(rule.menu_id.id)
            else:
                ids_by_state['restricted'].append(rule.menu_id.id)
        configured = {i for ids in ids_by_state.values() for i in ids}
        matching = {i for state in values for i in ids_by_state.get(state, [])}
        include_default = 'default' in values
        negative = operator in ('!=', 'not in')
        if not negative:
            if include_default:
                return ['|', ('id', 'in', list(matching)), ('id', 'not in', list(configured))]
            return [('id', 'in', list(matching))]
        if include_default:
            return [('id', 'in', list(configured - matching))]
        return [('id', 'not in', list(matching))]

    def _compute_dcs_xml_id(self):
        xmlids = self._get_menuitems_xmlids()
        for menu in self:
            menu.dcs_xml_id = xmlids.get(menu.id, False)

    def _search_dcs_xml_id(self, operator, value):
        if operator not in ('ilike', 'like', '=', '=ilike', '=like', 'not ilike'):
            raise NotImplementedError(_('Unsupported search on external ID.'))
        positive = operator != 'not ilike'
        op = 'ilike' if operator == 'not ilike' else operator
        imd = self.env['ir.model.data'].sudo()
        if isinstance(value, str) and '.' in value and op in ('=', 'ilike'):
            module, name = value.split('.', 1)
            records = imd.search([('model', '=', 'ir.ui.menu'), '|',
                                  '&', ('module', op, module), ('name', op, name),
                                  ('name', op, value)])
        else:
            records = imd.search([('model', '=', 'ir.ui.menu'), '|',
                                  ('name', op, value), ('module', op, value)])
        ids = records.mapped('res_id')
        return [('id', 'in' if positive else 'not in', ids)]

    def _dcs_action_labels(self):
        """Return {menu_id: "Type: Action name"} reading actions in batch."""
        type_labels = {
            'ir.actions.act_window': _('Window'),
            'ir.actions.server': _('Server'),
            'ir.actions.client': _('Client'),
            'ir.actions.act_url': _('URL'),
            'ir.actions.report': _('Report'),
        }
        by_model = defaultdict(set)
        menus = self.sudo()
        for menu in menus:
            if menu.action:
                by_model[menu.action._name].add(menu.action.id)
        names = {}
        for model, ids in by_model.items():
            # action names only, for an administrator screen
            for action in self.env[model].sudo().browse(ids).exists():
                names[(model, action.id)] = action.name
        result = {}
        for menu in menus:
            action = menu.action
            if action and (action._name, action.id) in names:
                result[menu.id] = '%s: %s' % (type_labels.get(action._name, action._name),
                                              names[(action._name, action.id)])
            else:
                result[menu.id] = False
        return result

    def _compute_dcs_action_info(self):
        labels = self._dcs_action_labels()
        for menu in self:
            menu.dcs_action_info = labels.get(menu.id, False)

    def _compute_dcs_child_count(self):
        data = self.with_context(active_test=False, **FULL_LIST_CTX)._read_group(
            [('parent_id', 'in', self.ids)], ['parent_id'], ['__count'])
        counts = {parent.id: count for parent, count in data}
        for menu in self:
            menu.dcs_child_count = counts.get(menu.id, 0)

    # ------------------------------------------------------------------
    # Cached, user-independent data
    # ------------------------------------------------------------------
    @api.model
    @api.ormcache()
    def _dcs_menu_structure(self):
        """{menu_id: (parent_id, has_action)} for all active menus.

        Cleared by Odoo whenever a menu is created, written or deleted.
        """
        menus = self.sudo().with_context(**FULL_LIST_CTX).search_fetch(
            [], ['parent_id', 'action'])
        by_model = defaultdict(set)
        for menu in menus:
            if menu.action:
                by_model[menu.action._name].add(menu.action.id)
        existing = set()
        for model, ids in by_model.items():
            existing.update((model, i) for i in self.env[model].sudo().browse(ids).exists().ids)
        return {
            menu.id: (
                menu.parent_id.id or False,
                bool(menu.action and (menu.action._name, menu.action.id) in existing),
            )
            for menu in menus
        }

    @api.model
    @api.ormcache()
    def _dcs_children_map(self):
        children = defaultdict(list)
        for menu_id, (parent_id, _has_action) in self._dcs_menu_structure().items():
            if parent_id:
                children[parent_id].append(menu_id)
        return {key: tuple(value) for key, value in children.items()}

    @api.model
    @api.ormcache()
    def _dcs_protected_menu_ids(self):
        """Menus that menu administrators always keep: Settings and this
        module's own menus (with their ancestors)."""
        imd = self.env['ir.model.data'].sudo()
        ids = set()
        for xmlid in PROTECTED_XMLIDS:
            res_id = imd._xmlid_to_res_id(xmlid, raise_if_not_found=False)
            if res_id:
                ids.add(res_id)
        ids.update(imd.search([('module', '=', MODULE),
                               ('model', '=', 'ir.ui.menu')]).mapped('res_id'))
        structure = self._dcs_menu_structure()
        for menu_id in list(ids):
            parent = structure.get(menu_id, (False,))[0]
            while parent:
                ids.add(parent)
                parent = structure.get(parent, (False,))[0]
        return frozenset(ids)

    @api.model
    @api.ormcache()
    def _dcs_rules_snapshot_cached(self):
        """Tuple of active rules as plain tuples (menu_id, hide_globally,
        hide_users, show_users, hide_companies, show_companies, show_groups,
        hide_groups). Cleared whenever a rule changes."""
        rules = self.env['dcs.menu.rule'].sudo().search_fetch(
            [('active', '=', True)],
            ['menu_id', 'hide_globally', 'hide_user_ids', 'show_user_ids',
             'hide_company_ids', 'show_company_ids', 'show_group_ids',
             'hide_group_ids'])
        return tuple(
            (
                rule.menu_id.id,
                rule.hide_globally,
                frozenset(rule.hide_user_ids.ids),
                frozenset(rule.show_user_ids.ids),
                frozenset(rule.hide_company_ids.ids),
                frozenset(rule.show_company_ids.ids),
                frozenset(rule.show_group_ids.ids),
                frozenset(rule.hide_group_ids.ids),
            )
            for rule in rules
        )

    # ------------------------------------------------------------------
    # Context helpers
    # ------------------------------------------------------------------
    @api.model
    def _dcs_active_company_ids(self):
        """Companies currently active for the user.

        1. ``allowed_company_ids`` from the context (every JSON-RPC call of the
           web client sends it);
        2. otherwise the ``cids`` cookie of the current request, which the web
           client sets when companies are switched (used by the plain HTTP
           request that loads the menus);
        3. otherwise the user's current company, like the web client.

        Only companies the user is allowed in are kept.
        """
        user = self.env.user
        allowed = set(user._get_company_ids())
        ids = []
        ctx_ids = self.env.context.get('allowed_company_ids')
        if ctx_ids:
            ids = [cid for cid in ctx_ids if cid in allowed]
        elif request:
            try:
                same_user = request.session.uid == self.env.uid
                cookie = request.cookies.get('cids') if same_user else None
            except (AttributeError, RuntimeError):
                cookie = None
            if cookie:
                for part in cookie.replace(',', '-').split('-'):
                    if part.strip().isdigit() and int(part) in allowed:
                        ids.append(int(part))
        if not ids:
            ids = [user.company_id.id]
        return frozenset(ids)

    @api.model
    def _dcs_debug(self):
        return bool(request.session.debug) if request else False

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------
    @api.model
    def _dcs_rule_reason(self, rule, uid, group_ids, company_ids):
        """Return the reason a rule hides the menu for this user, or None.

        ``company_ids`` is None when company rules must be ignored.
        """
        (_menu_id, hide_globally, hide_users, show_users, hide_companies,
         show_companies, show_groups, hide_groups) = rule
        if hide_globally:
            return 'global'
        if uid in hide_users:
            return 'user_hidden'
        if show_users and uid not in show_users:
            return 'user_not_allowed'
        if company_ids is not None and company_ids:
            if hide_companies and company_ids <= hide_companies:
                return 'company_hidden'
            if show_companies and company_ids.isdisjoint(show_companies):
                return 'company_not_allowed'
        if show_groups and group_ids.isdisjoint(show_groups):
            return 'group_not_allowed'
        if hide_groups and not group_ids.isdisjoint(hide_groups):
            return 'group_hidden'
        return None

    @api.model
    def _dcs_evaluate(self, debug, company_ids, skip_personal=False):
        """Evaluate visibility for ``self.env.user``.

        :param company_ids: frozenset of active companies, or None to ignore
                            company rules
        :return: (visible ids, {menu_id: reason} for every non-visible menu)
        """
        standard = super()._visible_menu_ids(debug)
        structure = self._dcs_menu_structure()
        reasons = {mid: 'standard' for mid in structure if mid not in standard}
        user = self.env.user
        if self.env.uid == SUPERUSER_ID:
            return frozenset(standard), reasons

        group_ids = frozenset(user._get_group_ids())
        protected = self._dcs_protected_menu_ids() if user._dcs_is_menu_manager() else frozenset()

        direct = {}
        for rule in self._dcs_rules_snapshot_cached():
            menu_id = rule[0]
            if menu_id not in standard or menu_id in protected:
                continue
            reason = self._dcs_rule_reason(rule, self.env.uid, group_ids, company_ids)
            if reason:
                direct[menu_id] = reason
        if not skip_personal:
            user_sudo = user.sudo()
            if user_sudo.dcs_allow_menu_preferences:
                for menu_id in user_sudo.dcs_personal_hidden_menu_ids.ids:
                    if menu_id in standard and menu_id not in protected:
                        direct.setdefault(menu_id, 'personal')
        if not direct:
            return frozenset(standard), reasons

        # hide the whole sub-tree of every hidden menu
        children = self._dcs_children_map()
        hidden = set(direct)
        reasons.update(direct)
        stack = list(direct)
        while stack:
            for child in children.get(stack.pop(), ()):
                if child not in hidden:
                    hidden.add(child)
                    if child in standard:
                        reasons[child] = 'parent'
                    stack.append(child)
        visible = set(standard) - hidden

        # a menu without action is only useful if one of its sub-menus is visible
        def depth(menu_id):
            level, parent = 0, structure.get(menu_id, (False,))[0]
            while parent:
                level += 1
                parent = structure.get(parent, (False,))[0]
            return level

        folders = sorted((mid for mid in visible
                          if mid in structure and not structure[mid][1]),
                         key=depth, reverse=True)
        for menu_id in folders:
            if not any(child in visible for child in children.get(menu_id, ())):
                if children.get(menu_id):
                    visible.discard(menu_id)
                    reasons[menu_id] = 'empty'
        return frozenset(visible), reasons

    @api.model
    @api.ormcache('self.env.uid', 'frozenset(self.env.user._get_group_ids())',
                    'debug', 'company_key', 'skip_personal')
    def _dcs_visible_menu_ids_cached(self, debug, company_key, skip_personal):
        company_ids = None if company_key is None else frozenset(company_key)
        return self._dcs_evaluate(debug, company_ids, skip_personal)[0]

    @api.model
    def _visible_menu_ids(self, debug=False):
        """Odoo's visible menus minus the ones restricted by this module."""
        if self.env.uid == SUPERUSER_ID:
            return super()._visible_menu_ids(debug)
        if self.env.context.get(CTX_SKIP_COMPANY):
            # stable per user: any of the user's companies may allow the menu
            company_key = tuple(sorted(self.env.user._get_company_ids()))
        else:
            company_key = tuple(sorted(self._dcs_active_company_ids()))
        return self._dcs_visible_menu_ids_cached(
            bool(debug), company_key, bool(self.env.context.get(CTX_SKIP_PERSONAL)))

    # ------------------------------------------------------------------
    # Web client entry points (cached by Odoo per user, not per company)
    # ------------------------------------------------------------------
    # Odoo (and modules such as website) cache load_menus / load_menus_root per
    # user only, at any position in the inheritance chain. Their result must
    # therefore never depend on the active companies: both are computed without
    # company rules, which are applied afterwards by the uncached entry points
    # of the web client (load_web_menus, session menu hash, bootstrap data).

    @api.model
    def load_menus(self, debug):
        return super(IrUiMenu, self.with_context(**{CTX_SKIP_COMPANY: True})).load_menus(debug)

    @api.model
    def load_menus_root(self):
        return super(IrUiMenu, self.with_context(**{CTX_SKIP_COMPANY: True})).load_menus_root()

    @api.model
    def _dcs_company_hidden_ids(self):
        """Menus hidden only because of company rules, for the active
        companies of the current request/context."""
        if self.env.uid == SUPERUSER_ID:
            return frozenset()
        debug = self._dcs_debug()
        without = self.with_context(**{CTX_SKIP_COMPANY: True})._visible_menu_ids(debug)
        with_companies = self.with_context(**{CTX_SKIP_COMPANY: False})._visible_menu_ids(debug)
        return frozenset(without - with_companies)

    @api.model
    def _dcs_filter_menu_dict(self, menus):
        """Remove company-hidden menus from a load_menus/load_web_menus dict."""
        removed = self._dcs_company_hidden_ids()
        if not removed or not any(key in removed for key in menus):
            return menus
        result = {}
        for key, menu in menus.items():
            if key in removed:
                continue
            new_menu = dict(menu)
            if 'children' in menu:
                new_menu['children'] = [c for c in menu['children'] if c not in removed]
            result[key] = new_menu
        return result

    @api.model
    def load_web_menus(self, debug):
        return self._dcs_filter_menu_dict(super().load_web_menus(debug))

    # ------------------------------------------------------------------
    # Administration API (menu tree client action)
    # ------------------------------------------------------------------
    @api.model
    def _dcs_check_manager(self):
        if not self.env.user._dcs_is_menu_manager():
            raise AccessError(_('Only menu administrators can manage menu visibility.'))

    @api.model
    def dcs_get_menu_tree(self, preview_user_id=False, preview_company_ids=False):
        """Data for the Menu Configuration tree, in one call.

        With ``preview_user_id``, also returns why each menu is hidden for that
        user with the given active companies.
        """
        self._dcs_check_manager()
        Menu = self.with_context(active_test=False, **FULL_LIST_CTX)
        menus = Menu.search_fetch([], ['name', 'parent_id', 'sequence', 'action',
                                       'active', 'group_ids', 'web_icon'])
        xmlids = menus._get_menuitems_xmlids()
        actions = menus._dcs_action_labels()
        rules = self.env['dcs.menu.rule'].with_context(active_test=False).search(
            [('menu_id', 'in', menus.ids)])
        rule_by_menu = {rule.menu_id.id: rule for rule in rules}
        personal_counts = defaultdict(int)
        users = self.env['res.users'].sudo().search(
            [('dcs_allow_menu_preferences', '=', True),
             ('dcs_personal_hidden_menu_ids', '!=', False)])
        for user in users:
            for menu_id in user.dcs_personal_hidden_menu_ids.ids:
                personal_counts[menu_id] += 1
        group_names = {g.id: g.full_name for g in menus.group_ids}
        protected = self._dcs_protected_menu_ids()

        preview = None
        preview_info = None
        if preview_user_id:
            preview_user = self.env['res.users'].browse(int(preview_user_id)).exists()
            if not preview_user or preview_user.share:
                raise AccessError(_('Preview is only available for internal users.'))
            user_companies = set(preview_user.sudo()._get_company_ids())
            cids = [int(c) for c in (preview_company_ids or []) if int(c) in user_companies]
            if not cids:
                cids = [preview_user.sudo().company_id.id]
            as_user = self.with_user(preview_user).with_context(allowed_company_ids=cids)
            visible, reasons = as_user._dcs_evaluate(False, frozenset(cids))
            preview = {'visible': visible, 'reasons': reasons}
            preview_info = {
                'user': preview_user.display_name,
                'companies': self.env['res.company'].sudo().browse(cids).mapped('name'),
            }

        nodes = []
        for menu in menus:
            rule = rule_by_menu.get(menu.id)
            node = {
                'id': menu.id,
                'name': menu.name,
                'parent_id': menu.parent_id.id or False,
                'sequence': menu.sequence,
                'active': menu.active,
                'xmlid': xmlids.get(menu.id, ''),
                'action': actions.get(menu.id) or '',
                'groups': [group_names[g] for g in menu.group_ids.ids if g in group_names],
                'protected': menu.id in protected,
                'personal_count': personal_counts.get(menu.id, 0),
                'rule': rule and {
                    'id': rule.id,
                    'active': rule.active,
                    'hide_globally': rule.hide_globally,
                    'hide_users': len(rule.hide_user_ids),
                    'show_users': len(rule.show_user_ids),
                    'hide_companies': len(rule.hide_company_ids),
                    'show_companies': len(rule.show_company_ids),
                    'show_groups': len(rule.show_group_ids),
                    'hide_groups': len(rule.hide_group_ids),
                    'summary': rule.summary,
                    'count': rule.restriction_count,
                } or False,
            }
            if preview is not None:
                if menu.id in preview['visible']:
                    node['preview'] = {'visible': True, 'reason': ''}
                else:
                    code = preview['reasons'].get(menu.id, 'standard' if menu.active else 'archived')
                    label = _('Menu archived') if code == 'archived' else str(REASONS.get(code, code))
                    node['preview'] = {'visible': False, 'code': code, 'reason': label}
            nodes.append(node)
        return {
            'nodes': nodes,
            'preview': preview_info,
            'multi_company': self.env.user.has_group('base.group_multi_company'),
        }

    def _dcs_get_or_create_rule(self):
        self.ensure_one()
        self._dcs_check_manager()
        Rule = self.env['dcs.menu.rule'].with_context(active_test=False)
        rule = Rule.search([('menu_id', '=', self.id)], limit=1)
        if not rule:
            rule = Rule.create({'menu_id': self.id})
        return rule

    def action_dcs_configure(self):
        """Open (and create if needed) the visibility rule of this menu."""
        self.ensure_one()
        rule = self._dcs_get_or_create_rule()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Visibility: %s', self.complete_name),
            'res_model': 'dcs.menu.rule',
            'res_id': rule.id,
            'view_mode': 'form',
            'views': [(self.env.ref('dcs_menu_management.dcs_menu_rule_view_form').id, 'form')],
            'target': 'new',
            'context': {'dialog_size': 'large'},
        }

    def action_dcs_toggle_hidden(self):
        """Hide for everyone / restore, without opening the rule."""
        self._dcs_check_manager()
        for menu in self:
            rule = menu._dcs_get_or_create_rule()
            if rule.hide_globally and rule.active:
                rule.hide_globally = False
            else:
                rule.write({'hide_globally': True, 'active': True})
        return True

    def action_dcs_reset(self):
        """Remove every restriction configured on these menus."""
        self._dcs_check_manager()
        self.env['dcs.menu.rule'].with_context(active_test=False).search(
            [('menu_id', 'in', self.ids)]).unlink()
        return True
