/** @odoo-module **/
// Copyright 2026 DevsCodeSpace (https://devscodespace.com)
// License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import { usePlugin } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { ORM } from "@web/core/orm_plugin";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";

/** "My Menus" entry in the user menu, for users allowed to hide menus. */
export function dcsMyMenusItem() {
    const action = useService("action");
    const orm = usePlugin(ORM);
    return {
        type: "item",
        id: "dcs_my_menus",
        description: _t("My Menus"),
        hide: !session.dcs_can_hide_menus,
        callback: async () => {
            const myMenus = await orm.call("res.users", "action_dcs_open_personal_menus", [[user.userId]]);
            await action.doAction(myMenus);
        },
        sequence: 55,
    };
}

registry.category("user_menuitems").add("dcs_my_menus", dcsMyMenusItem);
