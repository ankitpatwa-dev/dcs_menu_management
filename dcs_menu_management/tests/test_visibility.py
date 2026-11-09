# Copyright 2026 DevsCodeSpace (https://devscodespace.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import DcsMenuCase


@tagged('post_install', '-at_install', 'dcs_menu_management')
class TestMenuVisibility(DcsMenuCase):

    def test_00_baseline(self):
        """Without rules the module changes nothing."""
        everything_user = self.app | self.section | self.item_a | self.item_b | self.item_direct
        # Odoo itself keeps "Admin Item" (no groups) in the raw visible set even
        # though its parent is restricted; the web client cannot reach it.
        self.assertEqual(self.visible(self.user_1), everything_user | self.admin_item)
        # Parameters: no read access on ir.config_parameter; Admin App: groups
        self.assertNotIn(self.item_param, self.visible(self.user_1))
        self.assertNotIn(self.admin_app, self.visible(self.user_1))
        self.assertIn(self.admin_item, self.visible(self.admin))
        self.assertEqual(self.web_menus(self.user_1), everything_user)

    def test_01_hide_globally_and_restore(self):
        rule = self.rule(self.item_direct, hide_globally=True)
        for user in (self.user_1, self.user_2, self.admin, self.manager):
            self.assertNotIn(self.item_direct, self.visible(user, user.company_ids))
            self.assertNotIn(self.item_direct, self.web_menus(user))
        # restore: switch off, then archive/unarchive
        rule.hide_globally = False
        self.assertIn(self.item_direct, self.visible(self.user_1))
        rule.hide_globally = True
        rule.active = False
        self.assertIn(self.item_direct, self.visible(self.user_1))
        rule.unlink()
        self.assertIn(self.item_direct, self.web_menus(self.user_1))

    def test_02_toggle_shortcut(self):
        self.item_a.with_user(self.manager).action_dcs_toggle_hidden()
        self.assertNotIn(self.item_a, self.visible(self.user_1))
        self.item_a.with_user(self.manager).action_dcs_toggle_hidden()
        self.assertIn(self.item_a, self.visible(self.user_1))
        self.item_a.with_user(self.manager).action_dcs_reset()
        self.assertFalse(self.Rule.with_context(active_test=False).search(
            [('menu_id', '=', self.item_a.id)]))

    def test_03_hide_for_user(self):
        self.rule(self.item_a, hide_user_ids=[Command.set(self.user_1.ids)])
        self.assertNotIn(self.item_a, self.visible(self.user_1))
        self.assertIn(self.item_a, self.visible(self.user_2))
        self.assertIn(self.item_a, self.visible(self.user_grp))

    def test_04_show_only_for_users(self):
        self.rule(self.item_a, show_user_ids=[Command.set(self.user_2.ids)])
        self.assertIn(self.item_a, self.visible(self.user_2))
        self.assertNotIn(self.item_a, self.visible(self.user_1))
        self.assertNotIn(self.item_a, self.visible(self.admin))
        self.assertNotIn(self.item_a, self.web_menus(self.user_1))

    def test_05_hide_for_company(self):
        self.rule(self.item_a, hide_company_ids=[Command.set(self.company_a.ids)])
        self.assertNotIn(self.item_a, self.visible(self.user_2, self.company_a))
        self.assertIn(self.item_a, self.visible(self.user_2, self.company_b))
        self.assertIn(self.item_a, self.visible(self.user_1, self.main_company))

    def test_06_show_only_for_companies(self):
        self.rule(self.item_a, show_company_ids=[Command.set(self.company_b.ids)])
        self.assertIn(self.item_a, self.visible(self.user_2, self.company_b))
        self.assertNotIn(self.item_a, self.visible(self.user_2, self.company_a))
        self.assertNotIn(self.item_a, self.visible(self.user_1, self.main_company))

    def test_07_multiple_active_companies(self):
        """Visible as soon as one active company allows the menu."""
        self.rule(self.item_a, hide_company_ids=[Command.set(self.company_a.ids)])
        self.rule(self.item_b, show_company_ids=[Command.set(self.company_b.ids)])
        both = self.company_a | self.company_b
        self.assertIn(self.item_a, self.visible(self.user_2, both))
        self.assertIn(self.item_b, self.visible(self.user_2, both))
        self.assertNotIn(self.item_a, self.visible(self.user_2, self.company_a))
        self.assertNotIn(self.item_b, self.visible(self.user_2, self.company_a))
        # every active company hidden -> hidden
        self.rule(self.item_direct, hide_company_ids=[Command.set(both.ids)])
        self.assertNotIn(self.item_direct, self.visible(self.user_2, both))

    def test_08_company_switch_in_web_menus(self):
        """Odoo caches load_menus per user: company rules must still follow
        the active company, in both directions, and never poison caches."""
        self.rule(self.item_a, show_company_ids=[Command.set(self.company_b.ids)])
        self.rule(self.app, hide_company_ids=[Command.set(self.company_a.ids)])
        Menu = self.env['ir.ui.menu'].with_user(self.user_2)
        for _round in range(2):
            self.assertFalse(self.web_menus(self.user_2, self.company_a))
            self.assertIn(self.item_a, self.web_menus(self.user_2, self.company_b))
            # per-user cached methods stay company independent
            for cids in (self.company_a.ids, self.company_b.ids):
                menus = Menu.with_context(allowed_company_ids=cids)
                self.assertIn(self.app.id, menus.load_menus(False))
                self.assertIn(self.app.id, menus.load_menus_root()['all_menu_ids'])

    def test_09_unauthorized_company_in_context_ignored(self):
        """Companies the user is not allowed in are ignored."""
        self.rule(self.item_a, show_company_ids=[Command.set(self.main_company.ids)])
        menus = self.env['ir.ui.menu'].with_user(self.user_2).with_context(
            allowed_company_ids=self.main_company.ids)
        self.assertNotIn(self.item_a.id, menus._visible_menu_ids(False))

    def test_10_groups(self):
        self.rule(self.item_a, show_group_ids=[Command.set(self.group_test.ids)])
        self.assertIn(self.item_a, self.visible(self.user_grp))
        self.assertNotIn(self.item_a, self.visible(self.user_1))
        self.rule(self.item_b, hide_group_ids=[Command.set(self.group_test.ids)])
        self.assertNotIn(self.item_b, self.visible(self.user_grp))
        self.assertIn(self.item_b, self.visible(self.user_1))

    def test_11_group_change_updates_visibility(self):
        self.rule(self.item_a, show_group_ids=[Command.set(self.group_test.ids)])
        self.assertNotIn(self.item_a, self.visible(self.user_1))
        self.user_1.group_ids = [Command.link(self.group_test.id)]
        self.assertIn(self.item_a, self.visible(self.user_1))

    def test_12_combined_rules(self):
        """All conditions of a rule must allow the menu."""
        self.rule(self.item_a,
                  show_user_ids=[Command.set((self.user_1 | self.user_grp).ids)],
                  show_company_ids=[Command.set(self.main_company.ids)],
                  show_group_ids=[Command.set(self.group_test.ids)])
        self.assertIn(self.item_a, self.visible(self.user_grp, self.main_company))
        self.assertNotIn(self.item_a, self.visible(self.user_1, self.main_company), 'group missing')
        self.user_1.group_ids = [Command.link(self.group_test.id)]
        self.assertIn(self.item_a, self.visible(self.user_1, self.main_company))
        self.assertNotIn(self.item_a, self.visible(self.user_1, self.company_a), 'company not allowed')
        self.assertNotIn(self.item_a, self.visible(self.user_2, self.company_a), 'user not allowed')

    def test_13_parent_hides_children(self):
        self.rule(self.section, hide_user_ids=[Command.set(self.user_1.ids)])
        visible = self.visible(self.user_1)
        self.assertNotIn(self.section, visible)
        self.assertNotIn(self.item_a, visible)
        self.assertNotIn(self.item_b, visible)
        self.assertIn(self.item_direct, visible)
        self.assertIn(self.app, visible)
        # the children are not reachable via the web tree either
        self.assertEqual(self.web_menus(self.user_1), self.app | self.item_direct)
        # nor via a visibility-filtered menu search (Odoo 19 search() itself is unfiltered)
        found = self.env['ir.ui.menu'].with_user(self.user_1).search(
            [('id', 'in', self.test_menus.ids)])._filter_visible_menus()
        self.assertNotIn(self.item_a, found)
        roots = self.env['ir.ui.menu'].with_user(self.user_1).get_user_roots()
        self.assertIn(self.app, roots)

    def test_14_empty_folders_disappear(self):
        self.rule(self.item_a, hide_globally=True)
        self.rule(self.item_b, hide_globally=True)
        visible = self.visible(self.user_1)
        self.assertNotIn(self.section, visible, 'section without visible item')
        self.assertIn(self.app, visible)
        self.rule(self.item_direct, hide_globally=True)
        self.assertNotIn(self.app, self.visible(self.user_1), 'app without visible item')
        self.assertFalse(self.web_menus(self.user_1))

    def test_15_never_grants_visibility(self):
        """A "show only" rule cannot expose a menu Odoo hides."""
        self.rule(self.admin_app, show_user_ids=[Command.set(self.user_1.ids)])
        self.rule(self.item_param, show_user_ids=[Command.set(self.user_1.ids)])
        visible = self.visible(self.user_1)
        self.assertNotIn(self.admin_app, visible)
        self.assertNotIn(self.admin_item, self.web_menus(self.user_1))
        self.assertNotIn(self.item_param, visible)
        self.assertNotIn(self.admin_app, self.visible(self.admin), 'admin not in show list')

    def test_16_access_rights_unchanged(self):
        """Hiding a menu neither removes nor grants model access."""
        self.rule(self.item_a, hide_globally=True)
        self.rule(self.item_param, show_user_ids=[Command.set(self.user_1.ids)])
        partners = self.env['res.partner'].with_user(self.user_1)
        partners.check_access('read')
        self.assertTrue(partners.search([], limit=1))
        with self.assertRaises(AccessError):
            self.env['ir.config_parameter'].with_user(self.user_1).search([])

    def test_17_protected_menus_for_administrators(self):
        settings = self.env.ref('base.menu_administration')
        own_menu = self.env.ref('dcs_menu_management.menu_dcs_menu_configuration')
        self.rule(settings, hide_globally=True)
        Menu = self.env['ir.ui.menu']
        for user in (self.admin, self.manager):
            ids = Menu.with_user(user)._visible_menu_ids(False)
            self.assertIn(settings.id, ids)
            self.assertIn(own_menu.id, ids)
        erp_manager = self.env['res.users'].create({
            'name': 'Access Rights Only', 'login': 'dcs_erp_only',
            'group_ids': [Command.set([self.env.ref('base.group_erp_manager').id])]})
        self.assertNotIn(settings.id, Menu.with_user(erp_manager)._visible_menu_ids(False))

    def test_18_superuser_unaffected(self):
        self.rule(self.item_a, hide_globally=True)
        ids = self.env['ir.ui.menu'].sudo()._visible_menu_ids(False)
        # sudo keeps the current user (OdooBot here in tests is uid 1)
        self.assertIn(self.item_a.id, ids)

    def test_19_debug_only_menus_still_follow_odoo(self):
        technical = self.env.ref('base.menu_custom')
        Menu = self.env['ir.ui.menu'].with_user(self.admin)
        self.assertNotIn(technical.id, Menu._visible_menu_ids(False))
        self.assertIn(technical.id, Menu._visible_menu_ids(True))
        self.rule(technical, hide_user_ids=[Command.set(self.admin.ids)])
        self.assertNotIn(technical.id, Menu._visible_menu_ids(True))

    def test_20_archived_menu_rule(self):
        """Archiving a menu with a rule keeps the rule; deleting cascades."""
        rule = self.rule(self.item_b, hide_globally=True)
        self.item_b.active = False
        self.assertTrue(rule.exists())
        self.item_b.unlink()
        self.assertFalse(rule.exists())
        self.assertIn(self.item_a, self.visible(self.user_1))

    def test_21_client_context_cannot_bypass(self):
        """Context keys can be sent by any RPC client: none may lift a rule."""
        self.rule(self.item_a, hide_user_ids=[Command.set(self.user_2.ids)])
        # only a company user_2 does not belong to may see this menu
        self.rule(self.item_b, show_company_ids=[Command.set(self.main_company.ids)])
        self.rule(self.item_direct, show_company_ids=[Command.set(self.company_b.ids)])
        Menu = self.env['ir.ui.menu'].with_user(self.user_2).with_context(
            allowed_company_ids=self.company_a.ids,
            dcs_menu_skip_company=True, dcs_menu_disable=True)
        ids = Menu._visible_menu_ids(False)
        self.assertNotIn(self.item_a.id, ids)
        self.assertNotIn(self.item_b.id, ids, 'no company of the user allows it')
        self.assertIn(self.item_direct.id, ids, 'allowed in another company of the user')
        # per-user cached trees called directly over RPC
        tree = Menu.load_menus(False)
        self.assertNotIn(self.item_a.id, tree)
        self.assertNotIn(self.item_b.id, tree)
        roots = Menu.load_menus_root()['all_menu_ids']
        self.assertIn(self.app.id, roots)
