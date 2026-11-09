# Copyright 2026 DevsCodeSpace (https://devscodespace.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import Command
from odoo.tests.common import TransactionCase, new_test_user


class DcsMenuCase(TransactionCase):
    """Builds an isolated menu tree so tests do not depend on installed apps.

    DCS Test App (folder)
    ├── Section (folder)
    │   ├── Partners A (action on res.partner)
    │   └── Partners B (action on res.partner)
    ├── Direct Item (action on res.partner)
    └── Parameters (action on ir.config_parameter: admins only by ACL)
    DCS Admin App (folder, groups = Settings)
        └── Admin Item (action on res.partner)
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Menu = cls.env['ir.ui.menu'].with_context(**{'ir.ui.menu.full_list': True})
        cls.Rule = cls.env['dcs.menu.rule']
        cls.main_company = cls.env.ref('base.main_company')
        cls.company_a = cls.env['res.company'].create({'name': 'DCS Company A'})
        cls.company_b = cls.env['res.company'].create({'name': 'DCS Company B'})
        all_companies = (cls.main_company | cls.company_a | cls.company_b).ids

        cls.group_test = cls.env['res.groups'].create({'name': 'DCS Test Group'})
        cls.user_1 = new_test_user(
            cls.env, login='dcs_user_1', name='DCS User 1',
            groups='base.group_user', company_id=cls.main_company.id,
            company_ids=[Command.set(all_companies)])
        cls.user_2 = new_test_user(
            cls.env, login='dcs_user_2', name='DCS User 2',
            groups='base.group_user,base.group_multi_company',
            company_id=cls.company_a.id,
            company_ids=[Command.set([cls.company_a.id, cls.company_b.id])])
        cls.user_grp = new_test_user(
            cls.env, login='dcs_user_grp', name='DCS Grouped User',
            groups='base.group_user', company_id=cls.main_company.id)
        cls.user_grp.groups_id = [Command.link(cls.group_test.id)]
        cls.manager = new_test_user(
            cls.env, login='dcs_manager', name='DCS Menu Manager',
            groups='base.group_user,base.group_erp_manager,dcs_menu_management.group_menu_manager',
            company_id=cls.main_company.id, company_ids=[Command.set(all_companies)])
        cls.admin = new_test_user(
            cls.env, login='dcs_admin', name='DCS Admin',
            groups='base.group_user,base.group_system',
            company_id=cls.main_company.id, company_ids=[Command.set(all_companies)])

        def action(model, name):
            return cls.env['ir.actions.act_window'].create(
                {'name': name, 'res_model': model, 'view_mode': 'list,form'})

        act_partner = action('res.partner', 'DCS Partners')
        act_param = action('ir.config_parameter', 'DCS Parameters')
        ref = lambda act: '%s,%s' % (act._name, act.id)

        cls.app = cls.Menu.create({'name': 'DCS Test App', 'sequence': 1})
        cls.section = cls.Menu.create({'name': 'Section', 'parent_id': cls.app.id, 'sequence': 1})
        cls.item_a = cls.Menu.create({'name': 'Partners A', 'parent_id': cls.section.id,
                                      'action': ref(act_partner), 'sequence': 1})
        cls.item_b = cls.Menu.create({'name': 'Partners B', 'parent_id': cls.section.id,
                                      'action': ref(act_partner), 'sequence': 2})
        cls.item_direct = cls.Menu.create({'name': 'Direct Item', 'parent_id': cls.app.id,
                                           'action': ref(act_partner), 'sequence': 2})
        cls.item_param = cls.Menu.create({'name': 'Parameters', 'parent_id': cls.app.id,
                                          'action': ref(act_param), 'sequence': 3})
        cls.admin_app = cls.Menu.create({
            'name': 'DCS Admin App', 'sequence': 2,
            'groups_id': [Command.set([cls.env.ref('base.group_system').id])]})
        cls.admin_item = cls.Menu.create({'name': 'Admin Item', 'parent_id': cls.admin_app.id,
                                          'action': ref(act_partner)})
        cls.test_menus = (cls.app | cls.section | cls.item_a | cls.item_b | cls.item_direct
                          | cls.item_param | cls.admin_app | cls.admin_item)

    # ------------------------------------------------------------------
    def visible(self, user, companies=None, debug=False):
        """Test menus visible for ``user`` with the given active companies."""
        companies = companies or user.company_id
        menus = self.env['ir.ui.menu'].with_user(user).with_context(
            allowed_company_ids=companies.ids)
        ids = menus._visible_menu_ids(debug)
        return self.test_menus.filtered(lambda m: m.id in ids)

    def web_menus(self, user, companies=None):
        """Test menus present in the web client tree (load_web_menus)."""
        companies = companies or user.company_id
        menus = self.env['ir.ui.menu'].with_user(user).with_context(
            allowed_company_ids=companies.ids).load_web_menus(False)
        return self.test_menus.filtered(lambda m: m.id in menus)

    def rule(self, menu, **vals):
        vals['menu_id'] = menu.id
        return self.Rule.with_user(self.manager).create(vals)
