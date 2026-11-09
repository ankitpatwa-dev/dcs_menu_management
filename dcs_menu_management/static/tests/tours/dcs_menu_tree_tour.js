/** @odoo-module **/
// Copyright 2026 DevsCodeSpace. License LGPL-3.

import { registry } from "@web/core/registry";

const row = (name) => `.o_dcs_row:has(.o_dcs_name:contains("${name}"))`;

registry.category("web_tour.tours").add("dcs_menu_management_tree", {
    steps: () => [
        {
            content: "The menu tree is loaded",
            trigger: ".o_dcs_menu_tree .o_dcs_row",
        },
        {
            content: "Expand applications",
            trigger: ".o_dcs_menu_tree button:contains(Apps)",
            run: "click",
        },
        {
            content: "The test app is expanded",
            trigger: `${row("Direct Item")}`,
        },
        {
            content: "Search a menu",
            trigger: ".o_dcs_search_input",
            run: "edit Partners A",
        },
        {
            content: "Only the match and its ancestors remain",
            trigger: `.o_dcs_row.o_dcs_matched:contains("Partners A")`,
        },
        {
            content: "Hide it for everyone",
            trigger: `${row("Partners A")} .o_dcs_toggle_hidden`,
            run: "click",
        },
        {
            content: "Badge shows the global restriction",
            trigger: `${row("Partners A")} .badge:contains("Hidden for everyone")`,
        },
        {
            content: "Open the configuration",
            trigger: `${row("Partners A")} .o_dcs_configure`,
            run: "click",
        },
        {
            content: "Rule form opens in a dialog",
            trigger: ".modal .o_form_view div[name='hide_globally'] input:checked",
        },
        {
            content: "Restrict users",
            trigger: ".modal .o_notebook .nav-link[name='users']",
            run: "click",
        },
        {
            content: "Pick a user to hide the menu for",
            trigger: ".modal div[name='hide_user_ids'] input",
            run: "edit DCS User 1",
        },
        {
            trigger: ".ui-autocomplete a:contains('DCS User 1')",
            run: "click",
        },
        {
            content: "Save the rule",
            trigger: ".modal .o_form_button_save",
            run: "click",
        },
        {
            content: "Dialog closed, tree reloaded with the user badge",
            trigger: `body:not(:has(.modal)) ${row("Partners A")} .badge [data-icon=person]`,
        },
        {
            content: "Clear the search",
            trigger: ".o_dcs_search_input",
            run: "clear",
        },
        {
            content: "Preview as DCS User 2",
            trigger: ".o_dcs_preview_user",
            run: "selectByLabel DCS User 2",
        },
        {
            content: "Preview summary is shown",
            trigger: ".o_dcs_preview_summary:contains('DCS User 2')",
        },
        {
            content: "Show only hidden menus for that user",
            trigger: ".o_dcs_preview_filter",
            run: "select hidden",
        },
        {
            content: "The globally hidden menu is explained",
            trigger: `${row("Partners A")} .o_dcs_preview_cell:contains("Hidden for everyone")`,
        },
        {
            content: "Show it again",
            trigger: `${row("Partners A")} .o_dcs_toggle_hidden`,
            run: "click",
        },
        {
            content: "Global badge removed",
            trigger: `.o_dcs_menu_tree:not(:has(${row("Partners A")} .badge:contains("Hidden for everyone")))`,
        },
    ],
});

registry.category("web_tour.tours").add("dcs_menu_management_my_menus", {
    steps: () => [
        {
            content: "Open the user menu",
            trigger: "button.o_user_menu",
            run: "click",
        },
        {
            content: "Open My Menus",
            trigger: ".dropdown-item[data-menu='dcs_my_menus']",
            run: "click",
        },
        {
            content: "Hide the Section menu",
            trigger: ".modal .o_data_row:has(td[name='menu_path']:contains('DCS Test App/Section')):not(:has(td[name='menu_path']:contains('Partners'))) td[name='hidden'] .o_boolean_toggle input",
            run: "click",
        },
        {
            content: "Save and reload",
            trigger: ".modal button[name='action_apply']",
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Page reloaded without the dialog",
            trigger: "body:not(:has(.modal)) .o_main_navbar",
        },
    ],
});

registry.category("web_tour.tours").add("dcs_menu_management_shortcuts", {
    steps: () => [
        {
            content: "Favorites and recent icons are in the top bar",
            trigger: ".o_dcs_favorites_toggle",
        },
        {
            trigger: ".o_dcs_recent_toggle",
        },
        {
            content: "Open the applications menu",
            trigger: ".o_navbar_apps_menu button",
            run: "click",
        },
        {
            content: "Open the test application",
            trigger: ".o_app:contains('DCS Test App')",
            run: "click",
        },
        {
            content: "The application is open",
            trigger: ".o_list_view",
        },
        {
            content: "Open favorites",
            trigger: ".o_dcs_favorites_toggle",
            run: "click",
        },
        {
            content: "Add the current menu",
            trigger: ".o_dcs_toggle_current:contains('DCS Test App')",
            run: "click",
        },
        {
            content: "It is listed as a favorite",
            trigger: ".o_dcs_favorites .o_dcs_shortcut:contains('DCS Test App')",
        },
        {
            content: "Open recent menus",
            trigger: ".o_dcs_recent_toggle",
            run: "click",
        },
        {
            content: "The application is in the history",
            trigger: ".o_dcs_recent .o_dcs_shortcut_open:contains('DCS Test App')",
        },
    ],
});
