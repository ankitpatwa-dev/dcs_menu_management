/** @odoo-module **/
// Copyright 2026 DevsCodeSpace (https://devscodespace.com)
// License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import { Component, proxy } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { dcsMenuState } from "./menu_tracker";

class DcsShortcutsBase extends Component {
    static components = { Dropdown, DropdownItem };

    setup() {
        this.orm = useService("orm");
        this.menuService = useService("menu");
        this.menuState = dcsMenuState;
        this.state = proxy({ items: [], loaded: false });
    }

    async load() {
        const data = await this.orm.call("ir.ui.menu", "dcs_get_shortcuts", []);
        // only menus present in this user's menu tree (active companies included)
        this.state.items = data[this.kind].filter((item) => this.menuService.getMenu(item.id));
        this.state.loaded = true;
    }

    open(item) {
        this.menuService.selectMenu(item.id);
    }
}

export class DcsFavoritesSystray extends DcsShortcutsBase {
    static template = "dcs_menu_management.FavoritesSystray";
    kind = "favorites";

    get currentMenu() {
        const id = this.menuState.currentMenuId;
        const menu = id && this.menuService.getMenu(id);
        if (menu) {
            return menu;
        }
        const app = this.menuService.getCurrentApp();
        return app && app.actionID ? app : null;
    }

    get currentIsFavorite() {
        const menu = this.currentMenu;
        return Boolean(menu && this.state.items.some((item) => item.id === menu.id));
    }

    async toggleCurrent() {
        await this.orm.call("ir.ui.menu", "dcs_toggle_favorite", [this.currentMenu.id]);
        await this.load();
    }

    async remove(item) {
        await this.orm.call("ir.ui.menu", "dcs_toggle_favorite", [item.id]);
        await this.load();
    }
}

export class DcsRecentSystray extends DcsShortcutsBase {
    static template = "dcs_menu_management.RecentSystray";
    kind = "recent";
}

registry.category("systray").add(
    "dcs_menu_management.favorites",
    { Component: DcsFavoritesSystray, isDisplayed: () => Boolean(session.dcs_show_favorites) },
    { sequence: 26 }
);
registry.category("systray").add(
    "dcs_menu_management.recent",
    { Component: DcsRecentSystray, isDisplayed: () => Boolean(session.dcs_show_recent) },
    { sequence: 25 }
);
