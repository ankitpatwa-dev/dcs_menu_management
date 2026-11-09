/** @odoo-module **/
// Copyright 2026 DevsCodeSpace (https://devscodespace.com)
// License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { session } from "@web/session";

/** "My Menus" entry in the user menu, for users allowed to hide menus. */
export function dcsMyMenusItem(env) {
    return {
        type: "item",
        id: "dcs_my_menus",
        description: _t("My Menus"),
        hide: !session.dcs_can_hide_menus,
        callback: async () => {
            const action = await env.services.orm.call(
                "res.users",
                "action_dcs_open_personal_menus",
                [[user.userId]]
            );
            await env.services.action.doAction(action);
        },
        sequence: 55,
    };
}

registry.category("user_menuitems").add("dcs_my_menus", dcsMyMenusItem);
