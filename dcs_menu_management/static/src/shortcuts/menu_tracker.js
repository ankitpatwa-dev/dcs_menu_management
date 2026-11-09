/** @odoo-module **/
// Copyright 2026 DevsCodeSpace (https://devscodespace.com)
// License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import { reactive } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { menuService } from "@web/webclient/menus/menu_service";

/** Last menu the user opened through the menus (shared with the systray). */
export const dcsMenuState = reactive({ currentMenuId: null });

patch(menuService, {
    async start(env) {
        const menus = await super.start(...arguments);
        const selectMenu = menus.selectMenu;
        menus.selectMenu = async function (menu) {
            const target = typeof menu === "number" ? menus.getMenu(menu) : menu;
            const result = await selectMenu.call(this, menu);
            if (target && target.actionID) {
                dcsMenuState.currentMenuId = target.id;
                if (session.dcs_show_recent) {
                    env.services.orm.silent
                        .call("ir.ui.menu", "dcs_record_visit", [target.id])
                        .catch(() => {});
                }
            }
            return result;
        };
        return menus;
    },
});
