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
            result['dcs_can_hide_menus'] = bool(user.sudo().dcs_allow_menu_preferences)
        return result
