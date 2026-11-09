# Copyright 2026 DevsCodeSpace (https://devscodespace.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import DcsMenuCase


class DcsShortcutCase(DcsMenuCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        act = cls.env['ir.actions.act_window'].create(
            {'name': 'DCS Second', 'res_model': 'res.partner', 'view_mode': 'list,form'})
        cls.app2 = cls.Menu.create({'name': 'DCS Second App', 'sequence': 999})
        cls.app2_item = cls.Menu.create({'name': 'Second Item', 'parent_id': cls.app2.id,
                                         'action': 'ir.actions.act_window,%s' % act.id})
        cls.test_menus |= cls.app2 | cls.app2_item

    def root_order(self, user, companies=None):
        companies = companies or user.company_id
        menus = self.env['ir.ui.menu'].with_user(user).with_context(
            allowed_company_ids=companies.ids).load_web_menus(False)
        return [mid for mid in menus['root']['children'] if mid in (self.app.id, self.app2.id)]

    def enable(self, user, **flags):
        user.with_user(self.manager).write(flags)


@tagged('post_install', '-at_install', 'dcs_menu_management')
class TestAppOrder(DcsShortcutCase):

    def test_01_default_is_odoo_order(self):
        self.assertEqual(self.root_order(self.user_1), [self.app.id, self.app2.id])

    def test_02_global_order(self):
        self.env['dcs.menu.sequence'].with_user(self.manager)._dcs_set_order([self.app2.id, self.app.id])
        self.assertEqual(self.root_order(self.user_1), [self.app2.id, self.app.id])
        self.assertEqual(self.root_order(self.user_2, self.company_a), [self.app2.id, self.app.id])
        # Odoo's own sequence is untouched
        self.assertEqual(self.app2.sequence, 999)

    def test_03_personal_order_wins(self):
        Sequence = self.env['dcs.menu.sequence'].with_user(self.manager)
        Sequence._dcs_set_order([self.app2.id, self.app.id])
        Sequence._dcs_set_order([self.app.id, self.app2.id], self.user_1)
        self.assertEqual(self.root_order(self.user_1), [self.app.id, self.app2.id])
        self.assertEqual(self.root_order(self.user_grp), [self.app2.id, self.app.id])

    def test_04_unordered_apps_follow(self):
        """Apps missing from a saved order (e.g. installed later) come after."""
        self.env['dcs.menu.sequence'].with_user(self.manager)._dcs_set_order([self.app2.id])
        menus = self.env['ir.ui.menu'].with_user(self.user_1).load_web_menus(False)
        self.assertEqual(menus['root']['children'][0], self.app2.id)

    def test_05_wizard_global_and_reset(self):
        Wizard = self.env['dcs.menu.order.wizard'].with_user(self.manager).with_context(default_scope='global')
        wizard = Wizard.create({})
        lines = {line.menu_id: line for line in wizard.line_ids}
        self.assertIn(self.app, lines)
        self.assertIn(self.admin_app, lines, 'global order lists every application')
        lines[self.app2].sequence = -1
        wizard.action_apply()
        self.assertEqual(self.root_order(self.user_1), [self.app2.id, self.app.id])
        wizard = Wizard.create({})
        self.assertTrue(wizard.has_custom_order)
        self.assertEqual(wizard.line_ids[0].menu_id, self.app2)
        wizard.action_reset()
        self.assertEqual(self.root_order(self.user_1), [self.app.id, self.app2.id])

    def test_06_user_reorders_own_apps(self):
        self.enable(self.user_1, dcs_allow_menu_preferences=True)
        action = self.user_1.with_user(self.user_1).action_dcs_open_app_order()
        Wizard = self.env['dcs.menu.order.wizard'].with_user(self.user_1).with_context(action['context'])
        wizard = Wizard.create({})
        menus = wizard.line_ids.menu_id
        self.assertNotIn(self.admin_app, menus, 'only applications the user can see')
        wizard.line_ids.filtered(lambda l: l.menu_id == self.app2).sequence = -1
        wizard.action_apply()
        self.assertEqual(self.root_order(self.user_1), [self.app2.id, self.app.id])
        self.assertEqual(self.root_order(self.user_grp), [self.app.id, self.app2.id])

    def test_07_permissions(self):
        Sequence = self.env['dcs.menu.sequence']
        with self.assertRaises(AccessError):
            self.user_1.with_user(self.user_1).action_dcs_open_app_order()
        with self.assertRaises(AccessError):
            Sequence.with_user(self.user_1).create({'menu_id': self.app.id, 'user_id': self.user_1.id})
        self.enable(self.user_1, dcs_allow_menu_preferences=True)
        with self.assertRaises(AccessError):
            Sequence.with_user(self.user_1).create({'menu_id': self.app.id, 'user_id': False})
        with self.assertRaises(AccessError):
            Sequence.with_user(self.user_1).create({'menu_id': self.app.id, 'user_id': self.user_2.id})
        with self.assertRaises(AccessError):
            self.env['dcs.menu.order.wizard'].with_user(self.user_1).with_context(
                default_scope='global').create({})
        with self.assertRaises(AccessError):
            self.user_2.with_user(self.user_1).action_dcs_open_app_order()
        # the user can read the global order but cannot change it
        Sequence.with_user(self.manager)._dcs_set_order([self.app2.id, self.app.id])
        rows = Sequence.with_user(self.user_1).search([])
        self.assertTrue(rows)
        with self.assertRaises(AccessError):
            rows.with_user(self.user_1).unlink()

    def test_08_only_applications(self):
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.env['dcs.menu.sequence'].with_user(self.manager).create({'menu_id': self.item_a.id})


@tagged('post_install', '-at_install', 'dcs_menu_management')
class TestFavorites(DcsShortcutCase):

    def test_01_toggle_and_list(self):
        self.enable(self.user_1, dcs_show_favorites=True)
        Menu = self.env['ir.ui.menu'].with_user(self.user_1)
        self.assertTrue(Menu.dcs_toggle_favorite(self.item_a.id))
        self.assertTrue(Menu.dcs_toggle_favorite(self.item_direct.id))
        data = Menu.dcs_get_shortcuts()
        self.assertEqual([f['id'] for f in data['favorites']], [self.item_direct.id, self.item_a.id])
        self.assertEqual(data['favorites'][1]['path'], 'DCS Test App/Section')
        self.assertFalse(Menu.dcs_toggle_favorite(self.item_a.id))
        self.assertEqual(self.user_1.dcs_favorite_menu_ids, self.item_direct)

    def test_02_disabled(self):
        Menu = self.env['ir.ui.menu'].with_user(self.user_1)
        with self.assertRaises(AccessError):
            Menu.dcs_toggle_favorite(self.item_a.id)
        with self.assertRaises(AccessError):
            self.user_1.with_user(self.user_1).write(
                {'dcs_favorite_menu_ids': [Command.link(self.item_a.id)]})
        self.assertEqual(Menu.dcs_get_shortcuts(), {'favorites': [], 'recent': []})

    def test_03_never_exposes_hidden_menus(self):
        self.enable(self.user_1, dcs_show_favorites=True)
        Menu = self.env['ir.ui.menu'].with_user(self.user_1)
        with self.assertRaises(AccessError):
            Menu.dcs_toggle_favorite(self.item_param.id)  # no access to its model
        with self.assertRaises(AccessError):
            Menu.dcs_toggle_favorite(self.admin_item.id)  # parent restricted
        Menu.dcs_toggle_favorite(self.item_a.id)
        self.rule(self.item_a, hide_user_ids=[Command.set(self.user_1.ids)])
        self.assertFalse(Menu.dcs_get_shortcuts()['favorites'], 'hidden later: not shown')
        # an administrator setting a favorite the user cannot see changes nothing
        self.user_1.with_user(self.manager).dcs_favorite_menu_ids = [Command.link(self.item_param.id)]
        self.assertFalse(Menu.dcs_get_shortcuts()['favorites'])
        # removing a hidden favorite is still possible
        self.assertFalse(Menu.dcs_toggle_favorite(self.item_a.id))

    def test_04_other_users_and_commands(self):
        self.enable(self.user_1, dcs_show_favorites=True)
        self.enable(self.user_2, dcs_show_favorites=True)
        with self.assertRaises(AccessError):
            self.user_2.with_user(self.user_1).write(
                {'dcs_favorite_menu_ids': [Command.link(self.item_a.id)]})
        with self.assertRaises(UserError):
            self.user_1.with_user(self.user_1).write(
                {'dcs_favorite_menu_ids': [Command.create({'name': 'Injected'})]})
        with self.assertRaises(AccessError):
            self.user_1.with_user(self.user_1).write({'dcs_show_recent': True})

    def test_05_folder_menus_not_listed(self):
        self.enable(self.user_1, dcs_show_favorites=True)
        Menu = self.env['ir.ui.menu'].with_user(self.user_1)
        with self.assertRaises(AccessError):
            Menu.dcs_toggle_favorite(self.section.id)
        # set directly by an administrator: still not listed
        self.user_1.with_user(self.manager).dcs_favorite_menu_ids = [Command.link(self.section.id)]
        self.assertFalse(Menu.dcs_get_shortcuts()['favorites'], 'menus without action are not shortcuts')
        # an application (its first item's action opens it) can be a favorite
        self.assertTrue(Menu.dcs_toggle_favorite(self.app.id))
        self.assertEqual([f['id'] for f in Menu.dcs_get_shortcuts()['favorites']], [self.app.id])


@tagged('post_install', '-at_install', 'dcs_menu_management')
class TestRecentMenus(DcsShortcutCase):

    def test_01_records_most_recent_first(self):
        self.enable(self.user_1, dcs_show_recent=True)
        Menu = self.env['ir.ui.menu'].with_user(self.user_1)
        Recent = self.env['dcs.menu.recent'].with_user(self.user_1)
        self.assertTrue(Menu.dcs_record_visit(self.item_a.id))
        Recent.search([]).visit_date = '2020-01-01 00:00:00'
        self.assertTrue(Menu.dcs_record_visit(self.item_direct.id))
        recent = Menu.dcs_get_shortcuts()['recent']
        self.assertEqual([r['id'] for r in recent], [self.item_direct.id, self.item_a.id])
        Recent.search([('menu_id', '=', self.item_direct.id)]).visit_date = '2019-01-01 00:00:00'
        Menu.dcs_record_visit(self.item_a.id)
        self.assertEqual(len(Recent.search([])), 2, 'one row per menu')

    def test_02_limit(self):
        self.enable(self.user_1, dcs_show_recent=True)
        self.env['ir.config_parameter'].sudo().set_param('dcs_menu_management.recent_limit', '2')
        Menu = self.env['ir.ui.menu'].with_user(self.user_1)
        for menu in (self.item_a, self.item_b, self.item_direct):
            Menu.dcs_record_visit(menu.id)
        self.assertEqual(len(self.env['dcs.menu.recent'].with_user(self.user_1).search([])), 2)

    def test_03_disabled_or_invisible_not_recorded(self):
        Menu = self.env['ir.ui.menu'].with_user(self.user_1)
        self.assertFalse(Menu.dcs_record_visit(self.item_a.id), 'option off')
        self.enable(self.user_1, dcs_show_recent=True)
        self.assertFalse(Menu.dcs_record_visit(self.item_param.id), 'no access')
        self.assertFalse(Menu.dcs_record_visit(self.section.id), 'no action')
        self.rule(self.item_b, hide_globally=True)
        self.assertFalse(Menu.dcs_record_visit(self.item_b.id), 'hidden by a rule')
        self.assertFalse(self.env['dcs.menu.recent'].with_user(self.user_1).search([]))

    def test_04_private_to_each_user(self):
        for user in (self.user_1, self.admin):
            self.enable(user, dcs_show_recent=True)
            self.env['ir.ui.menu'].with_user(user).dcs_record_visit(self.item_direct.id)
        Recent = self.env['dcs.menu.recent']
        self.assertEqual(Recent.with_user(self.user_1).search([]).user_id, self.user_1)
        self.assertEqual(Recent.with_user(self.admin).search([]).user_id, self.admin,
                         'administrators do not see the history of others')
        other = Recent.with_user(self.admin).search([])
        with self.assertRaises(AccessError):
            other.with_user(self.user_1).read(['menu_id'])


@tagged('post_install', '-at_install', 'dcs_menu_management')
class TestUserMenuSettings(DcsShortcutCase):

    def test_01_hidden_menus_on_user_form(self):
        user = self.user_1.with_user(self.manager)
        user.dcs_hidden_menu_ids = [Command.set((self.item_a | self.item_direct).ids)]
        self.assertNotIn(self.item_a, self.visible(self.user_1))
        self.assertNotIn(self.item_direct, self.visible(self.user_1))
        rule = self.Rule.search([('menu_id', '=', self.item_a.id)])
        self.assertEqual(rule.hide_user_ids, self.user_1)
        user.invalidate_recordset(['dcs_hidden_menu_ids'])
        self.assertEqual(user.dcs_hidden_menu_ids, self.item_a | self.item_direct)
        user.dcs_hidden_menu_ids = [Command.set(self.item_direct.ids)]
        self.assertIn(self.item_a, self.visible(self.user_1))
        self.assertNotIn(self.item_direct, self.visible(self.user_1))

    def test_02_hidden_menus_field_is_admin_only(self):
        self.assertNotIn('dcs_hidden_menu_ids', self.env['res.users'].with_user(self.user_1).fields_get())

    def test_03_copy_wizard(self):
        source = self.user_1
        self.enable(source, dcs_allow_menu_preferences=True, dcs_show_favorites=True, dcs_show_recent=True)
        source.with_user(self.manager).write({
            'dcs_hidden_menu_ids': [Command.set(self.item_a.ids)],
            'dcs_personal_hidden_menu_ids': [Command.set(self.item_b.ids)],
            'dcs_favorite_menu_ids': [Command.set(self.item_direct.ids)],
        })
        self.env['dcs.menu.sequence'].with_user(self.manager)._dcs_set_order(
            [self.app2.id, self.app.id], source)
        action = source.with_user(self.manager).action_dcs_copy_menu_settings()
        Wizard = self.env['dcs.menu.copy.wizard'].with_user(self.manager).with_context(action['context'])
        wizard = Wizard.create({'user_ids': [Command.set((self.user_grp | source).ids)],
                                'copy_personal': True, 'copy_favorites': True,
                                'copy_app_order': True, 'copy_options': True})
        wizard.action_copy()
        target = self.user_grp
        self.assertTrue(target.dcs_allow_menu_preferences and target.dcs_show_favorites and target.dcs_show_recent)
        self.assertEqual(target.dcs_personal_hidden_menu_ids, self.item_b)
        self.assertEqual(target.dcs_favorite_menu_ids, self.item_direct)
        self.assertNotIn(self.item_a, self.visible(target))
        self.assertEqual(self.root_order(target), [self.app2.id, self.app.id])

    def test_04_copy_wizard_admin_only(self):
        with self.assertRaises(AccessError):
            self.user_1.with_user(self.user_2).action_dcs_copy_menu_settings()
        with self.assertRaises(AccessError):
            self.env['dcs.menu.copy.wizard'].with_user(self.user_2).create(
                {'source_user_id': self.user_1.id, 'user_ids': [Command.set(self.user_grp.ids)]})
