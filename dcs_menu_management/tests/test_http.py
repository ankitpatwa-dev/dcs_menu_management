# Copyright 2026 DevsCodeSpace (https://devscodespace.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import json

from odoo import Command
from odoo.tests import HttpCase, tagged

from .common import DcsMenuCase


@tagged('post_install', '-at_install', 'dcs_menu_management')
class TestMenuHttp(DcsMenuCase, HttpCase):

    def load_web_menus(self, cids=None):
        if cids is not None:
            self.opener.cookies.set('cids', '-'.join(str(c) for c in cids))
        response = self.url_open('/web/webclient/load_menus')
        self.assertEqual(response.status_code, 200)
        return {int(k) for k in json.loads(response.content) if k != 'root'}

    def test_01_web_menus_follow_company_cookie(self):
        """The menu request of the web client carries no context: the active
        companies come from the cookie set by the company switcher."""
        self.rule(self.item_a, show_company_ids=[Command.set(self.company_b.ids)])
        self.authenticate('dcs_user_2', 'dcs_user_2')
        self.assertNotIn(self.item_a.id, self.load_web_menus([self.company_a.id]))
        self.assertIn(self.item_a.id, self.load_web_menus([self.company_b.id]))
        self.assertIn(self.item_a.id, self.load_web_menus([self.company_a.id, self.company_b.id]))
        # a company the user does not belong to is ignored -> default company (A)
        self.assertNotIn(self.item_a.id, self.load_web_menus([self.main_company.id]))


    def test_02_rule_changes_reach_the_web_client(self):
        """Odoo 19 fetches menus with no-store on every page load: a rule
        change must be visible on the next request."""
        self.authenticate('dcs_user_1', 'dcs_user_1')
        self.assertIn(self.item_direct.id, self.load_web_menus())
        self.rule(self.item_direct, hide_user_ids=[Command.set(self.user_1.ids)])
        self.assertNotIn(self.item_direct.id, self.load_web_menus())

    def test_03_session_flag(self):
        self.authenticate('dcs_user_1', 'dcs_user_1')
        info = self.make_jsonrpc_request('/web/session/get_session_info')
        self.assertFalse(info.get('dcs_can_hide_menus'))
        self.user_1.dcs_allow_menu_preferences = True
        info = self.make_jsonrpc_request('/web/session/get_session_info')
        self.assertTrue(info.get('dcs_can_hide_menus'))

    def test_04_rpc_cannot_create_rules(self):
        self.authenticate('dcs_user_1', 'dcs_user_1')
        with self.assertRaises(Exception):
            self.make_jsonrpc_request('/web/dataset/call_kw/dcs.menu.rule/create', {
                'model': 'dcs.menu.rule', 'method': 'create',
                'args': [{'menu_id': self.item_a.id, 'hide_globally': True}], 'kwargs': {}})
        self.assertFalse(self.Rule.search([('menu_id', '=', self.item_a.id)]))

    def test_10_tree_tour(self):
        self.start_tour('/odoo/menu-management', 'dcs_menu_management_tree', login='dcs_admin')
        rule = self.Rule.search([('menu_id', '=', self.item_a.id)])
        self.assertFalse(rule.hide_globally)
        self.assertEqual(rule.hide_user_ids, self.user_1)

    def test_11_my_menus_tour(self):
        self.user_1.dcs_allow_menu_preferences = True
        self.start_tour('/odoo', 'dcs_menu_management_my_menus', login='dcs_user_1')
        self.assertEqual(self.user_1.dcs_personal_hidden_menu_ids, self.section)
