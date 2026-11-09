# Copyright 2026 DevsCodeSpace (https://devscodespace.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import DcsMenuCase


@tagged('post_install', '-at_install', 'dcs_menu_management')
class TestPersonalMenus(DcsMenuCase):

    def allow(self, user):
        user.with_user(self.manager).dcs_allow_menu_preferences = True

    def test_01_hide_and_restore(self):
        self.allow(self.user_1)
        me = self.user_1.with_user(self.user_1)
        me.write({'dcs_personal_hidden_menu_ids': [Command.link(self.item_a.id)]})
        self.assertNotIn(self.item_a, self.visible(self.user_1))
        self.assertIn(self.item_a, self.visible(self.user_2), 'other users unaffected')
        me.write({'dcs_personal_hidden_menu_ids': [Command.unlink(self.item_a.id)]})
        self.assertIn(self.item_a, self.visible(self.user_1))

    def test_02_permission_required(self):
        me = self.user_1.with_user(self.user_1)
        with self.assertRaises(AccessError):
            me.write({'dcs_personal_hidden_menu_ids': [Command.link(self.item_a.id)]})
        with self.assertRaises(AccessError):
            me.write({'dcs_allow_menu_preferences': True})

    def test_03_revoked_permission_ignores_preferences(self):
        self.allow(self.user_1)
        self.user_1.with_user(self.user_1).write(
            {'dcs_personal_hidden_menu_ids': [Command.link(self.item_a.id)]})
        self.assertNotIn(self.item_a, self.visible(self.user_1))
        self.user_1.with_user(self.manager).dcs_allow_menu_preferences = False
        self.assertIn(self.item_a, self.visible(self.user_1))

    def test_04_cannot_touch_other_users(self):
        self.allow(self.user_1)
        self.allow(self.user_2)
        with self.assertRaises(AccessError):
            self.user_2.with_user(self.user_1).write(
                {'dcs_personal_hidden_menu_ids': [Command.link(self.item_a.id)]})
        # administrators may reset someone's preferences
        self.user_2.with_user(self.user_2).write(
            {'dcs_personal_hidden_menu_ids': [Command.link(self.item_a.id)]})
        self.user_2.with_user(self.manager).action_dcs_reset_personal_menus()
        self.assertFalse(self.user_2.dcs_personal_hidden_menu_ids)
        with self.assertRaises(AccessError):
            self.user_2.with_user(self.user_1).action_dcs_reset_personal_menus()

    def test_05_no_menu_changes_through_preferences(self):
        self.allow(self.user_1)
        me = self.user_1.with_user(self.user_1)
        for command in (Command.create({'name': 'Injected'}),
                        Command.update(self.item_a.id, {'name': 'Renamed'}),
                        Command.delete(self.item_a.id)):
            with self.assertRaises(UserError):
                me.write({'dcs_personal_hidden_menu_ids': [command]})
        self.assertEqual(self.item_a.name, 'Partners A')

    def test_06_self_readable_in_preferences(self):
        self.allow(self.user_1)
        data = self.user_1.with_user(self.user_1).read(
            ['dcs_allow_menu_preferences', 'dcs_personal_hidden_menu_ids'])
        self.assertTrue(data[0]['dcs_allow_menu_preferences'])

    def test_07_wizard(self):
        self.allow(self.user_1)
        Wizard = self.env['dcs.menu.personal.wizard'].with_user(self.user_1)
        wizard = Wizard.create({})
        menus = wizard.line_ids.menu_id
        self.assertIn(self.item_a, menus)
        self.assertNotIn(self.item_param, menus, 'menus Odoo hides are not offered')
        self.assertNotIn(self.admin_app, menus)
        wizard.line_ids.filtered(lambda l: l.menu_id == self.section).hidden = True
        action = wizard.action_apply()
        self.assertEqual(action['tag'], 'reload')
        self.assertEqual(self.user_1.dcs_personal_hidden_menu_ids, self.section)
        visible = self.visible(self.user_1)
        self.assertNotIn(self.item_a, visible)
        self.assertIn(self.item_direct, visible)
        # reopening: the hidden section is listed and checked
        wizard2 = Wizard.create({})
        line = wizard2.line_ids.filtered(lambda l: l.menu_id == self.section)
        self.assertTrue(line.hidden)
        wizard2.action_show_all()
        wizard2.action_apply()
        self.assertFalse(self.user_1.dcs_personal_hidden_menu_ids)

    def test_08_wizard_requires_permission(self):
        Wizard = self.env['dcs.menu.personal.wizard'].with_user(self.user_1)
        with self.assertRaises(AccessError):
            Wizard.default_get(['line_ids'])
        with self.assertRaises(AccessError):
            self.user_1.with_user(self.user_1).action_dcs_open_personal_menus()
        self.allow(self.user_1)
        action = self.user_1.with_user(self.user_1).action_dcs_open_personal_menus()
        self.assertEqual(action['res_model'], 'dcs.menu.personal.wizard')
        with self.assertRaises(AccessError):
            self.user_2.with_user(self.user_1).action_dcs_open_personal_menus()

    def test_09_wizard_isolated_per_user(self):
        self.allow(self.user_1)
        self.allow(self.user_2)
        wizard = self.env['dcs.menu.personal.wizard'].with_user(self.user_1).create({})
        with self.assertRaises(AccessError):
            wizard.with_user(self.user_2).read(['line_ids'])

    def test_10_admin_protected_menus_not_hideable_personally(self):
        settings = self.env.ref('base.menu_administration')
        self.admin.with_user(self.admin).dcs_allow_menu_preferences = True
        self.admin.with_user(self.admin).write(
            {'dcs_personal_hidden_menu_ids': [Command.link(settings.id)]})
        self.assertIn(settings.id, self.env['ir.ui.menu'].with_user(self.admin)._visible_menu_ids(False))
