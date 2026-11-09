# Copyright 2026 DevsCodeSpace (https://devscodespace.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import hashlib

from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        result = super().session_info()
        user = self.env.user
        if user and not user.share:
            # shows the "My Menus" entry in the user menu
            result['dcs_can_hide_menus'] = bool(user.sudo().dcs_allow_menu_preferences)
            # The browser caches /web/webclient/load_menus/<hash> for a long
            # time. Odoo's hash ignores the active companies; include the menus
            # hidden by company rules so a company switch loads the right tree.
            hashes = result.get('cache_hashes') or {}
            if hashes.get('load_menus'):
                removed = self.env['ir.ui.menu']._dcs_company_hidden_ids()
                if removed:
                    seed = '%s|%s' % (hashes['load_menus'], ','.join(map(str, sorted(removed))))
                    hashes['load_menus'] = hashlib.sha512(seed.encode()).hexdigest()[:64]
        return result

    def webclient_rendering_context(self):
        context = super().webclient_rendering_context()
        if context.get('menu_data'):
            context['menu_data'] = self.env['ir.ui.menu']._dcs_filter_menu_dict(context['menu_data'])
        return context
