# Copyright 2026 DevsCodeSpace (https://devscodespace.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        result = super().session_info()
        user = self.env.user
        if user and not user.share:
            # shows the "My Menus" entry in the user menu
            user_sudo = user.sudo()
            result['dcs_can_hide_menus'] = bool(user_sudo.dcs_allow_menu_preferences)
            # favorite / recent menus in the top bar
            result['dcs_show_favorites'] = bool(user_sudo.dcs_show_favorites)
            result['dcs_show_recent'] = bool(user_sudo.dcs_show_recent)
        return result
