/** @odoo-module **/
// Copyright 2026 DevsCodeSpace (https://devscodespace.com)
// License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import { Component, onWillStart, proxy, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";

const FILTERS = [
    ["all", _t("All menus")],
    ["configured", _t("With restrictions")],
    ["hidden", _t("Hidden for everyone")],
    ["users", _t("User restrictions")],
    ["companies", _t("Company restrictions")],
    ["groups", _t("Group restrictions")],
    ["personal", _t("Hidden personally")],
    ["suspended", _t("Archived rules")],
    ["odoo_groups", _t("With Odoo groups")],
    ["inactive", _t("Archived menus")],
];

function ruleIsActive(rule) {
    return rule && rule.active && rule.count > 0;
}

export class DcsMenuTree extends Component {
    static template = "dcs_menu_management.MenuTree";
    static components = { Layout };
    props = useProps(standardActionServiceProps);

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.filters = FILTERS;
        this.state = proxy({
            loading: true,
            nodes: {},
            roots: [],
            expanded: {},
            search: "",
            filter: "all",
            previewFilter: "all",
            previewUserId: "",
            previewCompanyIds: [],
            previewInfo: null,
            users: [],
            companies: {},
            multiCompany: false,
        });
        onWillStart(async () => {
            await Promise.all([this.load(), this.loadUsers()]);
        });
    }

    // ------------------------------------------------------------------
    // Data
    // ------------------------------------------------------------------
    async load() {
        const args = [];
        const kwargs = {};
        if (this.state.previewUserId) {
            kwargs.preview_user_id = parseInt(this.state.previewUserId);
            kwargs.preview_company_ids = this.state.previewCompanyIds;
        }
        const data = await this.orm.call("ir.ui.menu", "dcs_get_menu_tree", args, kwargs);
        const nodes = {};
        for (const node of data.nodes) {
            node.children = [];
            nodes[node.id] = node;
        }
        const roots = [];
        for (const node of data.nodes) {
            if (node.parent_id && nodes[node.parent_id]) {
                nodes[node.parent_id].children.push(node.id);
            } else {
                roots.push(node.id);
            }
        }
        const order = (a, b) => nodes[a].sequence - nodes[b].sequence || a - b;
        for (const node of data.nodes) {
            node.children.sort(order);
        }
        roots.sort(order);
        // restriction inherited from an ancestor
        const markInherited = (id, inherited) => {
            const node = nodes[id];
            node.inherited = inherited;
            const own = ruleIsActive(node.rule);
            for (const child of node.children) {
                markInherited(child, inherited || own);
            }
        };
        roots.forEach((id) => markInherited(id, false));
        Object.assign(this.state, {
            nodes,
            roots,
            previewInfo: data.preview,
            multiCompany: data.multi_company,
            loading: false,
        });
    }

    async loadUsers() {
        const users = await this.orm.searchRead(
            "res.users",
            [["share", "=", false]],
            ["name", "login", "company_id", "company_ids"],
            { order: "name", context: { active_test: true } }
        );
        const companyIds = [...new Set(users.flatMap((u) => u.company_ids))];
        const companies = companyIds.length
            ? await this.orm.read("res.company", companyIds, ["name"])
            : [];
        this.state.users = users;
        this.state.companies = Object.fromEntries(companies.map((c) => [c.id, c.name]));
    }

    // ------------------------------------------------------------------
    // Tree rows
    // ------------------------------------------------------------------
    get stats() {
        const nodes = Object.values(this.state.nodes);
        return {
            total: nodes.length,
            configured: nodes.filter((n) => ruleIsActive(n.rule)).length,
            hidden: nodes.filter((n) => ruleIsActive(n.rule) && n.rule.hide_globally).length,
            previewHidden: this.state.previewInfo
                ? nodes.filter((n) => n.active && n.preview && !n.preview.visible).length
                : 0,
        };
    }

    matchesFilter(node) {
        const rule = node.rule;
        switch (this.state.filter) {
            case "configured":
                return ruleIsActive(rule);
            case "hidden":
                return ruleIsActive(rule) && rule.hide_globally;
            case "users":
                return ruleIsActive(rule) && (rule.hide_users || rule.show_users);
            case "companies":
                return ruleIsActive(rule) && (rule.hide_companies || rule.show_companies);
            case "groups":
                return ruleIsActive(rule) && (rule.hide_groups || rule.show_groups);
            case "personal":
                return node.personal_count > 0;
            case "suspended":
                return rule && !rule.active && rule.count > 0;
            case "odoo_groups":
                return node.groups.length > 0;
            case "inactive":
                return !node.active;
        }
        return true;
    }

    matchesPreview(node) {
        if (!this.state.previewInfo || this.state.previewFilter === "all" || !node.preview) {
            return true;
        }
        return this.state.previewFilter === "visible" ? node.preview.visible : !node.preview.visible;
    }

    get isFiltering() {
        return (
            this.state.search.trim() !== "" ||
            this.state.filter !== "all" ||
            (this.state.previewInfo && this.state.previewFilter !== "all")
        );
    }

    get rows() {
        const { nodes, roots } = this.state;
        const rows = [];
        if (this.isFiltering) {
            const term = this.state.search.trim().toLowerCase();
            const shown = new Set();
            const matched = new Set();
            for (const node of Object.values(nodes)) {
                const textOk =
                    !term ||
                    node.name.toLowerCase().includes(term) ||
                    node.xmlid.toLowerCase().includes(term) ||
                    node.action.toLowerCase().includes(term);
                if (textOk && this.matchesFilter(node) && this.matchesPreview(node)) {
                    matched.add(node.id);
                    let current = node;
                    while (current) {
                        shown.add(current.id);
                        current = current.parent_id && nodes[current.parent_id];
                    }
                }
            }
            const walk = (id, depth) => {
                if (!shown.has(id)) {
                    return;
                }
                const node = nodes[id];
                rows.push({ node, depth, expanded: true, hasChildren: node.children.length > 0, matched: matched.has(id), context: !matched.has(id) });
                node.children.forEach((child) => walk(child, depth + 1));
            };
            roots.forEach((id) => walk(id, 0));
            return rows;
        }
        const walk = (id, depth) => {
            const node = nodes[id];
            const expanded = !!this.state.expanded[id];
            rows.push({ node, depth, expanded, hasChildren: node.children.length > 0, matched: false, context: false });
            if (expanded) {
                node.children.forEach((child) => walk(child, depth + 1));
            }
        };
        roots.forEach((id) => walk(id, 0));
        return rows;
    }

    get previewUser() {
        return this.state.users.find((u) => u.id === parseInt(this.state.previewUserId));
    }

    get previewUserCompanies() {
        const user = this.previewUser;
        if (!user) {
            return [];
        }
        return user.company_ids.map((id) => ({ id, name: this.state.companies[id] || `#${id}` }));
    }

    badgesFor(node) {
        const rule = node.rule;
        const badges = [];
        if (rule && rule.count > 0 && !rule.active) {
            badges.push({ cls: "text-bg-secondary", icon: "archive", label: _t("Rule archived"), title: rule.summary });
            return badges;
        }
        if (!ruleIsActive(rule)) {
            return badges;
        }
        if (rule.hide_globally) {
            badges.push({ cls: "text-bg-danger", icon: "visibility_off", label: _t("Hidden for everyone"), title: rule.summary });
        }
        if (rule.hide_users || rule.show_users) {
            const parts = [];
            if (rule.show_users) parts.push(_t("only %s", rule.show_users));
            if (rule.hide_users) parts.push(_t("−%s", rule.hide_users));
            badges.push({ cls: "text-bg-warning", icon: "person", label: parts.join(" "), title: rule.summary });
        }
        if (rule.hide_companies || rule.show_companies) {
            const parts = [];
            if (rule.show_companies) parts.push(_t("only %s", rule.show_companies));
            if (rule.hide_companies) parts.push(_t("−%s", rule.hide_companies));
            badges.push({ cls: "text-bg-info", icon: "business", label: parts.join(" "), title: rule.summary });
        }
        if (rule.hide_groups || rule.show_groups) {
            const parts = [];
            if (rule.show_groups) parts.push(_t("only %s", rule.show_groups));
            if (rule.hide_groups) parts.push(_t("−%s", rule.hide_groups));
            badges.push({ cls: "text-bg-primary", icon: "group", label: parts.join(" "), title: rule.summary });
        }
        return badges;
    }

    nodeIcon(row) {
        if (row.depth === 0) {
            return "apps";
        }
        if (row.hasChildren) {
            return row.expanded ? "folder_open" : "folder";
        }
        return row.node.action ? "description" : "article";
    }

    // ------------------------------------------------------------------
    // Handlers
    // ------------------------------------------------------------------
    toggle(id) {
        this.state.expanded[id] = !this.state.expanded[id];
    }

    expandAll() {
        const expanded = {};
        for (const node of Object.values(this.state.nodes)) {
            if (node.children.length) {
                expanded[node.id] = true;
            }
        }
        this.state.expanded = expanded;
    }

    expandApps() {
        const expanded = {};
        for (const id of this.state.roots) {
            expanded[id] = true;
        }
        this.state.expanded = expanded;
    }

    collapseAll() {
        this.state.expanded = {};
    }

    clearFilters() {
        this.state.search = "";
        this.state.filter = "all";
        this.state.previewFilter = "all";
    }

    onSearchInput(ev) {
        this.state.search = ev.target.value;
    }

    onFilterChange(ev) {
        this.state.filter = ev.target.value;
    }

    onPreviewFilterChange(ev) {
        this.state.previewFilter = ev.target.value;
    }

    async onPreviewUserChange(ev) {
        this.state.previewUserId = ev.target.value;
        const user = this.previewUser;
        this.state.previewCompanyIds = user && user.company_id ? [user.company_id[0]] : [];
        this.state.previewFilter = "all";
        await this.load();
    }

    async onPreviewCompanyToggle(companyId, ev) {
        const ids = new Set(this.state.previewCompanyIds);
        if (ev.target.checked) {
            ids.add(companyId);
        } else {
            ids.delete(companyId);
        }
        if (!ids.size) {
            ev.target.checked = true;
            return;
        }
        this.state.previewCompanyIds = [...ids];
        await this.load();
    }

    async toggleHidden(node) {
        await this.orm.call("ir.ui.menu", "action_dcs_toggle_hidden", [[node.id]]);
        const nowHidden = !(ruleIsActive(node.rule) && node.rule.hide_globally);
        this.notification.add(
            nowHidden
                ? _t("“%s” is now hidden for everyone.", node.name)
                : _t("“%s” is visible again.", node.name),
            { type: nowHidden ? "warning" : "success" }
        );
        await this.load();
    }

    async configure(node) {
        const action = await this.orm.call("ir.ui.menu", "action_dcs_configure", [[node.id]]);
        await this.action.doAction(action, { onClose: () => this.load() });
    }

    async openRules() {
        await this.action.doAction("dcs_menu_management.action_dcs_menu_rule");
    }

    async openList() {
        await this.action.doAction("dcs_menu_management.action_dcs_ir_ui_menu");
    }
}

registry.category("actions").add("dcs_menu_management.menu_tree", DcsMenuTree);
