# Copyright 2026 DevsCodeSpace (https://devscodespace.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import new_test_user, tagged
from odoo.tools import mute_logger

from .common import DcsMenuCase


@tagged('post_install', '-at_install', 'dcs_menu_management')
class TestMenuAdministration(DcsMenuCase):

    def test_01_only_managers_configure(self):
        with self.assertRaises(AccessError):
            self.Rule.with_user(self.user_1).create({'menu_id': self.item_a.id, 'hide_globally': True})
        with self.assertRaises(AccessError):
            self.item_a.with_user(self.user_1).action_dcs_toggle_hidden()
        with self.assertRaises(AccessError):
            self.item_a.with_user(self.user_1).action_dcs_configure()
        rule = self.rule(self.item_a, hide_globally=True)
        with self.assertRaises(AccessError):
            rule.with_user(self.user_1).write({'hide_globally': False})
        with self.assertRaises(AccessError):
            rule.with_user(self.user_1).unlink()
        with self.assertRaises(AccessError):
            rule.with_user(self.user_1).read(['hide_globally'])
        # Settings administrators manage rules without the extra group
        rule.with_user(self.admin).write({'hide_globally': False})

    def test_02_one_rule_per_menu(self):
        self.rule(self.item_a, hide_globally=True)
        with mute_logger('odoo.sql_db'), self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.rule(self.item_a, hide_globally=True)

    def test_03_contradictions_rejected(self):
        with self.assertRaises(ValidationError):
            self.rule(self.item_a, hide_user_ids=[Command.set(self.user_1.ids)],
                      show_user_ids=[Command.set(self.user_1.ids)])
        with self.assertRaises(ValidationError):
            self.rule(self.item_a, hide_company_ids=[Command.set(self.company_a.ids)],
                      show_company_ids=[Command.set(self.company_a.ids)])
        portal = self.env['res.users'].create({
            'name': 'Portal', 'login': 'dcs_portal',
            'group_ids': [Command.set([self.env.ref('base.group_portal').id])]})
        with self.assertRaises(ValidationError):
            self.rule(self.item_a, hide_user_ids=[Command.set(portal.ids)])

    def test_04_company_isolation_of_configuration(self):
        restricted_manager = new_test_user(
            self.env, login='dcs_manager_main_only',
            groups='base.group_user,dcs_menu_management.group_menu_manager',
            company_id=self.main_company.id,
            company_ids=[Command.set(self.main_company.ids)])
        self.assertEqual(restricted_manager.company_ids, self.main_company)
        # Odoo 19 already refuses to link a company the user cannot access
        # (AccessError); the module's own check raises ValidationError.
        try:
            with self.env.cr.savepoint():
                self.Rule.with_user(restricted_manager).create({
                    'menu_id': self.item_a.id,
                    'show_company_ids': [Command.set(self.company_b.ids)]})
        except (AccessError, ValidationError):
            pass
        else:
            self.fail('A company outside the user\'s companies was accepted in a rule.')

    def test_05_configure_action_reuses_rule(self):
        menu = self.item_a.with_user(self.manager)
        first = menu.action_dcs_configure()
        second = menu.action_dcs_configure()
        self.assertEqual(first['res_id'], second['res_id'])
        self.assertEqual(first['res_model'], 'dcs.menu.rule')
        rule = self.Rule.browse(first['res_id'])
        rule.active = False
        self.assertEqual(menu.action_dcs_configure()['res_id'], rule.id, 'archived rule reused')

    def test_06_visibility_state_and_search(self):
        self.rule(self.item_a, hide_globally=True)
        self.rule(self.item_b, hide_user_ids=[Command.set(self.user_1.ids)])
        rule_c = self.rule(self.item_direct, show_group_ids=[Command.set(self.group_test.ids)])
        rule_c.active = False
        Menu = self.Menu.with_user(self.manager)
        menus = Menu.browse((self.item_a | self.item_b | self.item_direct | self.section).ids)
        self.assertEqual(menus.mapped('dcs_visibility_state'),
                         ['hidden', 'restricted', 'suspended', 'default'])
        scope = [('id', 'in', self.test_menus.ids)]
        self.assertEqual(Menu.search(scope + [('dcs_visibility_state', '=', 'hidden')]), self.item_a)
        self.assertEqual(Menu.search(scope + [('dcs_visibility_state', '=', 'restricted')]), self.item_b)
        default = Menu.search(scope + [('dcs_visibility_state', '=', 'default')])
        self.assertNotIn(self.item_a, default)
        self.assertIn(self.section, default)
        not_hidden = Menu.search(scope + [('dcs_visibility_state', '!=', 'hidden')])
        self.assertNotIn(self.item_a, not_hidden)
        self.assertIn(self.item_b, not_hidden)
        self.assertEqual(
            Menu.search(scope + [('dcs_rule_ids.hide_user_ids', 'ilike', 'DCS User 1')]), self.item_b)

    def test_07_xml_id_search(self):
        menu = self.env.ref('base.menu_users')
        Menu = self.Menu.with_user(self.manager)
        self.assertEqual(menu.with_user(self.manager).dcs_xml_id, 'base.menu_users')
        self.assertIn(menu, Menu.search([('dcs_xml_id', 'ilike', 'base.menu_users')]))
        self.assertIn(menu, Menu.search([('dcs_xml_id', 'ilike', 'menu_users')]))

    def test_08_tree_data(self):
        self.rule(self.item_a, hide_user_ids=[Command.set(self.user_1.ids)])
        with self.assertRaises(AccessError):
            self.env['ir.ui.menu'].with_user(self.user_1).dcs_get_menu_tree()
        data = self.env['ir.ui.menu'].with_user(self.manager).dcs_get_menu_tree()
        nodes = {n['id']: n for n in data['nodes']}
        self.assertEqual(nodes[self.item_a.id]['rule']['hide_users'], 1)
        self.assertEqual(nodes[self.item_a.id]['parent_id'], self.section.id)
        self.assertIn('DCS Partners', nodes[self.item_a.id]['action'])
        self.assertTrue(nodes[self.env.ref('base.menu_administration').id]['protected'])
        self.assertIsNone(data['preview'])

    def test_09_preview_explains_reasons(self):
        self.rule(self.item_a, hide_user_ids=[Command.set(self.user_2.ids)])
        self.rule(self.section, show_company_ids=[Command.set(self.company_a.ids)])
        Menu = self.env['ir.ui.menu'].with_user(self.manager)
        data = Menu.dcs_get_menu_tree(preview_user_id=self.user_2.id,
                                      preview_company_ids=self.company_b.ids)
        nodes = {n['id']: n for n in data['nodes']}
        self.assertEqual(nodes[self.section.id]['preview']['code'], 'company_not_allowed')
        self.assertEqual(nodes[self.item_b.id]['preview']['code'], 'parent')
        self.assertEqual(nodes[self.item_param.id]['preview']['code'], 'standard')
        self.assertTrue(nodes[self.item_direct.id]['preview']['visible'])
        data = Menu.dcs_get_menu_tree(preview_user_id=self.user_2.id,
                                      preview_company_ids=self.company_a.ids)
        nodes = {n['id']: n for n in data['nodes']}
        self.assertEqual(nodes[self.item_a.id]['preview']['code'], 'user_hidden')
        self.assertTrue(nodes[self.item_b.id]['preview']['visible'])
        self.assertEqual(data['preview']['companies'], ['DCS Company A'])
        # preview matches what the user really gets
        real = self.visible(self.user_2, self.company_a)
        previewed = self.test_menus.filtered(lambda m: nodes[m.id]['preview']['visible'])
        self.assertEqual(real, previewed)
        # companies outside the user's are ignored, default company used
        data = Menu.dcs_get_menu_tree(preview_user_id=self.user_2.id,
                                      preview_company_ids=self.main_company.ids)
        self.assertEqual(data['preview']['companies'], ['DCS Company A'])

    def test_10_personal_count_in_tree(self):
        self.user_1.with_user(self.manager).write({
            'dcs_allow_menu_preferences': True,
            'dcs_personal_hidden_menu_ids': [Command.link(self.item_direct.id)]})
        data = self.env['ir.ui.menu'].with_user(self.manager).dcs_get_menu_tree()
        nodes = {n['id']: n for n in data['nodes']}
        self.assertEqual(nodes[self.item_direct.id]['personal_count'], 1)
        rule = self.rule(self.item_direct, hide_globally=False)
        self.assertEqual(rule.personal_user_ids, self.user_1)

    def test_11_fields_hidden_from_regular_users(self):
        fields = self.env['ir.ui.menu'].with_user(self.user_1).fields_get()
        self.assertNotIn('dcs_rule_ids', fields)
        self.assertNotIn('dcs_visibility_state', fields)

    def test_12_cache_invalidation(self):
        """Visibility is cached; every rule change must be seen at once."""
        self.assertIn(self.item_a, self.visible(self.user_1))
        rule = self.rule(self.item_a, hide_user_ids=[Command.set(self.user_1.ids)])
        self.assertNotIn(self.item_a, self.visible(self.user_1))
        rule.hide_user_ids = [Command.set(self.user_2.ids)]
        self.assertIn(self.item_a, self.visible(self.user_1))
        self.assertNotIn(self.item_a, self.visible(self.user_2, self.company_a))

    def test_13_query_count_is_stable(self):
        """Once cached, evaluating menus does not hit the database per menu."""
        for index in range(30):
            menu = self.Menu.create({'name': 'Bulk %s' % index, 'parent_id': self.section.id})
            self.rule(menu, hide_user_ids=[Command.set(self.user_1.ids)])
        Menu = self.env['ir.ui.menu'].with_user(self.user_1).with_context(
            allowed_company_ids=self.main_company.ids)
        Menu._visible_menu_ids(False)
        with self.assertQueryCount(0):
            Menu._visible_menu_ids(False)
            Menu._visible_menu_ids(False)
