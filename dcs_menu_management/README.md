# Advanced Menu Management (`dcs_menu_management`)

Odoo 18.0 · Community and Enterprise · LGPL-3 · by [DevsCodeSpace](https://devscodespace.com)

Decide who sees which Odoo menu, and in which order, without editing XML, Python or security
groups. Hide menus for everyone, for some users, companies or security groups; change the
application order for everyone or per user; give users favorite and recent menus in the top
bar; let selected users hide the menus they never use; copy menu settings between users. The module **only narrows** Odoo's standard menu visibility: it never
shows a menu, an action or a record to someone Odoo would not show it to.

---

## Contents

1. [Features](#features)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Administrator guide](#administrator-guide)
5. [Personal preferences guide](#personal-preferences-guide)
6. [Visibility rules and precedence](#visibility-rules-and-precedence)
7. [Security](#security)
8. [Technical architecture](#technical-architecture)
9. [Performance](#performance)
10. [Testing](#testing)
11. [Troubleshooting](#troubleshooting)
12. [Known limitations](#known-limitations)
13. [Support and license](#support-and-license)

---

## Features

| Area | What you get |
|---|---|
| Menu tree | Settings › Menu Management › Menu Configuration: every app, section and item with external ID, action, Odoo groups and restriction badges. Expand/collapse, search (name, external ID, action), filters (restricted, hidden, users, companies, groups, personal, archived rules/menus). |
| Quick actions | Hide for everyone / show again in one click; open the rule of any menu in a dialog. |
| Preview as user | Pick an internal user and any of their companies: every menu shows *Visible* or the reason it is hidden. |
| Global visibility | *Hide for Everyone* on any menu, reversible at any time; archive a rule to suspend it. |
| Users | *Hide for Users* and *Show Only for Users* (many2many). |
| Companies | *Hide for Companies* and *Show Only for Companies*, evaluated on the companies active in the company switcher. |
| Security groups | *Show Only for Groups* and *Hide for Groups*, combined with (never replacing) the menu's own Odoo groups. |
| Personal menus | *Hide Menus Through Preferences* per user; a **My Menus** entry in the user menu and a **My Menus** tab in preferences. |
| List view | Settings › Menu Management › All Menus: native list with status badges, filters, search by user/company/group, group by parent menu. |
| Rules list | Settings › Menu Management › Visibility Rules: every configured rule, filters, who changed it last. |
| Application order | Settings › Menu Management › Application Order: drag applications into the order everyone sees (menu bar, apps menu, home screen). Per-user order from the user form or, for allowed users, *My Menus › Reorder My Apps*. Odoo's own menu sequence is never modified. |
| Favorite menus | Star icon in the top bar: add the current menu, open a favorite, remove it with ×. Administrators can also set favorites on the user form. |
| Recent menus | History icon in the top bar: the last 10 menus the user opened (configurable), stored per user on the server, private to the user. |
| User form | *Menu Management* tab: hidden menus for this user, options (personal hiding, favorites, recent), favorites, personal hidden menus, application order, copy settings. |
| Copy settings | Copy hidden menus, personal hidden menus, favorites, application order and options from one user to others. |
| User Menu Settings | Settings › Menu Management › User Menu Settings: switch personal hiding, favorites and recent menus on/off for many users, see and reset their hidden menus. |

## Installation

Requirements: Odoo 18.0 (Community or Enterprise). Dependencies: only the standard `web`
module. No Python or JavaScript library to install.

1. Copy the `dcs_menu_management` folder into one of your addons paths
   (or unzip the downloaded archive there).
2. Restart the Odoo server.
3. Activate the developer mode, open **Apps › Update Apps List**.
4. Search for *Advanced Menu Management* and click **Activate**.

Command line alternative:

```bash
odoo-bin -c odoo.conf -d <database> -i dcs_menu_management --stop-after-init
```

Upgrading to a newer version of the module: replace the folder, restart, then
`odoo-bin -c odoo.conf -d <database> -u dcs_menu_management --stop-after-init`
(or **Upgrade** in Apps). Rules and personal preferences are kept.

## Configuration

### Who can configure

* **Settings administrators** (`Administration / Settings`) can always configure menus.
* The **Menu Manager** group (user form › *Menu Management* section) lets other users
  configure menus. They also need access to the Settings app
  (`Administration / Access Rights`) to reach the Menu Management menu.

The module does not change any standard Odoo group.

### Menu entries

| Menu | Purpose |
|---|---|
| Settings › Menu Management › **Menu Configuration** | Interactive tree, quick hide/show, rule dialog, preview as user |
| Settings › Menu Management › **All Menus** | List of every menu with status and filters |
| Settings › Menu Management › **Visibility Rules** | Every configured rule |
| Settings › Menu Management › **Application Order** | Order of the applications for everyone |
| Settings › Menu Management › **User Menu Settings** | Per-user switches: personal hiding, favorites, recent menus |

## Administrator guide

### Hide a menu for everyone

1. Open **Menu Configuration** and find the menu (expand the app or type in the search box).
2. Click the **eye-slash** button on its row. The badge *Hidden for everyone* appears.
3. To restore it, click the **eye** button on the same row.

The menu and all its sub-menus disappear for every user at their next page load. The same
action exists in **All Menus** (row buttons and form header).

### Restrict a menu to users, companies or groups

1. Click the **sliders** button on the menu's row. The *Visibility* dialog opens.
2. Use the tabs:
   * **Users**: *Hide for Users* and/or *Show Only for Users*.
   * **Companies**: *Hide for Companies* and/or *Show Only for Companies*.
   * **Security Groups**: *Show Only for Groups* and/or *Hide for Groups*.
   * **Personal Preferences**: users who hid this menu themselves (read only).
   * **Notes**: why the restriction exists.
3. **Save**. Empty lists mean "no restriction".

The dialog also shows the menu's **Odoo Standard Groups** (read only) so you can see what
Odoo already requires.

### Suspend or remove a restriction

* *Visibility Rules* › open the rule › **Archive**: the rule stops applying but is kept.
* *All Menus* › open the menu › **Remove Restrictions**: deletes the rule.

### Check the result before telling users

In **Menu Configuration**, choose a user under **Preview as user** (and, for multi-company
users, tick the active companies). Each menu then shows *Visible* or the reason it is hidden:

| Reason | Meaning |
|---|---|
| Odoo groups or access rights | Odoo itself hides it (menu groups, model access, debug-only) |
| Hidden for everyone | *Hide for Everyone* rule |
| Hidden for this user / User not in "Show only" | User lists |
| Hidden for the company / Company not in "Show only" | Company lists |
| Group not in "Show only" / Hidden for a group | Group lists |
| Personal preference | The user hid it in *My Menus* |
| Parent menu hidden | One of its parents is hidden |
| All sub-menus hidden | Section without any visible item |

Use the *Hidden for this user* filter to list only the menus that user does not get.

### Allow users to hide menus themselves

* **Personal Preferences** menu: remove the *Allowed* filter and switch on
  **Hide Menus Through Preferences** for the users concerned; or
* user form › **Menu Visibility** tab.

From the same places you can see a user's hidden menus and **Reset Personal Menus**.
Removing the permission suspends the user's personal choices (they are kept and apply
again if the permission is given back).

### Change the application order

* **Everyone:** Settings › Menu Management › **Application Order**. Drag the applications with
  the handles, then **Save and Reload**. **Reset Order** returns to Odoo's order.
* **One user:** user form › *Menu Management* tab › **Application Order**. A personal order
  replaces the global one for that user; **Reset Order** returns them to the global order.
* Applications missing from a saved order (for example installed later) come after the ordered
  ones, in Odoo's order. Only applications (top-level menus) are ordered; Odoo's
  `ir.ui.menu.sequence` is never written.

### Configure a user (user form)

Settings › Users › a user › **Menu Management** tab:

* **Hidden Menus**: menus hidden for this user. Saved as *Hide for Users* on each menu's rule,
  so Menu Configuration shows the same thing.
* **Options**: *Hide Menus Through Preferences*, *Favorite Menus*, *Recent Menus*.
* **Favorite Menus** and **Personally Hidden Menus** of the user.
* Buttons: **Application Order**, **Copy Menu Settings to Other Users**, **Reset Personal Menus**.

Settings › Menu Management › **User Menu Settings** shows the same switches for all users in an
editable list.

### Copy menu settings to other users

User form › *Menu Management* › **Copy Menu Settings to Other Users**: choose the target users
and what to copy (hidden menus, personal hidden menus, favorites, application order, options).
Hidden menus are added to the targets; the other lists replace theirs.

### Favorite and recent menus

* Switch on **Favorite Menus** / **Recent Menus** per user (user form or User Menu Settings).
  The star and history icons appear in their top bar after a reload.
* Favorites and recent menus only ever list menus the user can open right now (all visibility
  rules, active companies, and the menu's parents are checked), so they cannot be used to reach
  a hidden menu.
* Number of recent menus: system parameter `dcs_menu_management.recent_limit` (default 10, max 50).
* Recent menus are private: record rules restrict each user, administrators included, to their
  own history.

## Personal preferences guide

For users who have the **Hide Menus Through Preferences** permission:

1. Click your avatar (top right) › **My Menus**.
2. Switch on **Hide** for the menus you do not use (applications, sections and their items
   are listed). Hiding a section hides everything under it.
3. Click **Save and Reload**.

To bring menus back, open **My Menus** again and switch them off, or click **Show All**.
**Reorder My Apps** (in My Menus, or *My Menus* tab of the preferences) puts your applications
in your own order.

**Favorites** (if enabled for you): open a menu, click the **star** in the top bar, then
**Add “…” to favorites**. Click a favorite to open it, **×** to remove it.

**Recent menus** (if enabled for you): click the **history** icon in the top bar to reopen one of
the last menus you used.
You can also open **Preferences › My Menus** and remove menus from *Hidden Menus*, then
reload the page.

Your choices only change your own menu bar. They do not change what you are allowed to do,
and other users are not affected.

## Visibility rules and precedence

A menu is shown to a user only if **all** of the following allow it, checked in this order
(the first one that hides it is the reason shown in the preview):

1. **Odoo standard visibility**: menu groups, read access on the action's model,
   debug-only menus (`base.group_no_one`). The module starts from Odoo's result and never
   adds to it.
2. **Protected menus**: *Settings* and the module's own menus (with their parents) are
   never hidden for menu administrators, whatever the rules say, so nobody can lock
   themselves out.
3. **Hide for Everyone**.
4. **Users**: hidden if the user is in *Hide for Users*; if *Show Only for Users* is set,
   hidden for anyone not in it.
5. **Companies** (active companies of the company switcher):
   * *Hide for Companies*: hidden when **every** active company is in the list;
   * *Show Only for Companies*: hidden when **no** active company is in the list.
   In other words, with several active companies the menu stays visible as long as one of
   them allows it.
6. **Groups**: if *Show Only for Groups* is set, the user must be in one of them; hidden if
   the user is in any *Hide for Groups* group.
7. **Personal preferences** of the user (only while the user has the permission).
8. **Hierarchy**: a hidden menu hides all its sub-menus; a menu without action whose
   sub-menus are all hidden is hidden too, so no empty section is left.

Consequences:

* "Show only" lists can only narrow; they cannot override Odoo groups or another hiding
  condition.
* A user cannot be in both the *Hide* and *Show only* list of the same rule (rejected on save).
* Rules apply to internal users only; portal and public users never see backend menus.
* The superuser (`__system__`, used by scripts and crons) is not filtered.

## Security

* **Configuration**: `dcs.menu.rule` is only accessible to Settings administrators and Menu
  Managers (model access rights), and its create/write/unlink also check the group in code.
  Menu managers never get write access to `ir.ui.menu`, so they cannot change menu groups.
* **Personal preferences**: the hidden menus field is self-writable through Odoo's
  `SELF_WRITEABLE_FIELDS` mechanism, with extra server-side checks: only for the user
  themself, only with the permission, and only *link/unlink/clear/set* commands (a user
  cannot create, rename or delete menus through it). The permission itself can only be
  changed by menu administrators. Writing another user's preferences requires being a
  menu administrator.
* **Wizard isolation**: the *My Menus* wizard has record rules limiting each user to their
  own records.
* **No bypass from the client**: the context keys the module uses internally cannot lift a
  restriction; the most they do is evaluate company rules against all the user's companies.
* **Multi-company**: active companies are validated against the user's allowed companies;
  rule company lists can only contain companies the configuring user has access to.
* **sudo()** is only used to read the cached rule snapshot, menu metadata (action names,
  external IDs) and the user's own preference fields during evaluation. Results never grant
  anything: they are subtracted from Odoo's own visible set.
* **Hiding a menu is not access control.** Users can still open records they have access to
  through links, smart buttons, URLs or the API. Protect data with access rights and record
  rules; use this module to tidy menus.

## Technical architecture

```
dcs_menu_management/
├── models/
│   ├── dcs_menu_rule.py     dcs.menu.rule: one rule per menu (unique), lists of users,
│   │                        companies, groups; manager checks; cache invalidation
│   ├── ir_ui_menu.py        visibility engine (inherits ir.ui.menu), admin API for the tree
│   ├── dcs_menu_sequence.py application order (global rows and per-user rows)
│   ├── dcs_menu_recent.py   recently opened menus (one row per user and menu, private)
│   ├── res_users.py         options, personal hidden menus, favorites, admin hidden menus,
│   │                        self-write guards
│   └── ir_http.py           session flag, company-aware menu hash, bootstrap menu data
├── wizard/                  My Menus, Application Order, Copy Menu Settings
├── security/                Menu Manager group, ACLs, wizard record rules
├── views/                   rule views, ir.ui.menu list/form/search, user views, menus
├── data/                    client action (Menu Configuration, path /odoo/menu-management)
├── demo/                    demo user allowed to hide menus, archived example rule
├── static/src/menu_tree/    OWL client action (tree, filters, preview)
├── static/src/user_menu/    "My Menus" user menu entry
├── static/src/shortcuts/    favorites (star) and recent (history) top-bar dropdowns, menu-click tracker
├── static/tests/tours/      browser tours
└── tests/                   Python and HTTP tests
```

**Engine.** Odoo computes menu visibility in `ir.ui.menu._visible_menu_ids()` (cached per
set of groups) and every entry point uses it: `search()` on menus, `get_user_roots()`,
`load_menus()` (menu bar, home screen, command palette) and `load_menus_root()`. The module
overrides `_visible_menu_ids()`: it takes Odoo's result and removes the menus hidden by
rules, their descendants and the sections left empty. The result is cached with
`tools.ormcache` per user, set of groups, debug mode, active companies and personal flag.

**Company switching.** Odoo caches `load_menus()` per user only, and other modules (for
example `website` with `load_menus_root()`) add their own per-user caches anywhere in the
inheritance chain. These methods are therefore always computed with company rules
evaluated against *all* the user's companies, which is stable per user. The exact active
companies are applied afterwards by the uncached entry points of the web client:
`load_web_menus()` (the `/web/webclient/load_menus` request), the menu hash in
`session_info()` (the browser caches menus by that hash, so it now changes with the active
companies) and `webclient_rendering_context()`. Active companies come from the context
(`allowed_company_ids`), otherwise from the `cids` cookie set by the company switcher,
otherwise the user's current company; companies the user is not allowed in are ignored.

**Application order, favorites, recent.** `load_menus()` returns the applications in the
user's order (personal rows, else global rows, else Odoo's order; cached per user). Every menu
click in the web client goes through the menu service's `selectMenu()`, which the module wraps
to record recent menus (one RPC, only when the option is on) and to know the current menu for
"Add to favorites". `dcs_get_shortcuts`, `dcs_toggle_favorite` and `dcs_record_visit` work on the
current user only and check that each menu can be opened (visible, parents visible, has an
action or is an application).

**Caches and invalidation.** Three user-independent caches (menu structure, protected
menus, rule snapshot) and the per-user result live in Odoo's registry cache. They are
cleared by Odoo when menus change and by the module when a rule or a personal preference
changes (`registry.clear_cache()`), on every worker.

**Data model.** Rules are stored in their own table (`dcs_menu_rule`), never on menus, so
module upgrades that reload menus from XML keep the configuration, and uninstalling the
module leaves `ir_ui_menu` untouched. Deleting a menu deletes its rule (`ondelete=cascade`).

## Performance

Measured on Odoo 18.0 Community, Python 3.13, PostgreSQL 16, 2 CPUs:

| Database | Cold menu load (`load_web_menus`) | Warm (cached) |
|---|---|---|
| 13 apps, 489 menus, no rule | 81 ms, 56 queries | 2.2 ms, 0 queries |
| 13 apps, 489 menus, 200 rules | 97 ms, 40 queries | 2.2 ms, 0 queries |
| 3,550 menus, 1,000 rules hiding menus | 346 ms (Odoo alone: 328 ms) | 15 ms (Odoo alone: 26 ms) |

Evaluation is one pass over cached tuples; no ORM query per menu or per rule. The
Menu Configuration tree loads all menus in one call (190 ms for 3,550 menus) and only
renders expanded branches.

## Testing

```bash
odoo-bin -c odoo.conf -d <test-db> -i dcs_menu_management \
         --test-tags /dcs_menu_management --stop-after-init
```

74 automated tests (`tests/`), including three browser tours (need Chrome/Chromium and the
`websocket-client` Python package):

* global hide/restore, quick toggle, user, company (single and several active companies,
  unauthorised companies), group, combined rules, group change, parent/child and empty
  sections, debug-only menus, archived/deleted menus;
* never granting visibility, access rights unchanged, protected menus, superuser;
* personal preferences: hide/restore, permission, revocation, other users, forbidden
  commands, wizard, wizard isolation;
* administration: manager-only configuration (ORM and RPC), one rule per menu,
  contradictions, company isolation, status search, external ID search, tree data, preview
  reasons equal to the real result, cache invalidation, zero queries once cached;
* HTTP: menus follow the `cids` cookie, menu hash changes with rules and companies,
  session flag, client context cannot lift a rule;
* application order: default, global, personal over global, apps added later, wizard and reset,
  user reordering own apps, permissions (own only, global read-only, others refused);
* favorites: toggle and list, option off, never exposing hidden/unreachable menus, other users,
  forbidden commands, sections vs applications;
* recent menus: order, one row per menu, limit, option off, invisible menus not recorded,
  private to each user (administrators included);
* user form: hidden menus field (rules), admin-only field, copy wizard and its permissions;
* tours: Menu Configuration (search, hide, configure, preview, restore), My Menus, and the
  favorites/recent top-bar icons.

## Troubleshooting

| Symptom | Check |
|---|---|
| A change does not appear for a user | Users must reload the page (F5). Menus are loaded once per page. |
| A menu is still hidden after removing the rule | Use **Preview as user**: the reason may be Odoo's own access, a parent menu, a group rule or the user's personal preferences. |
| A "Show only for users" user does not see the menu | Rules never add visibility: the user also needs the menu's Odoo groups and read access to the action's model (reason *Odoo groups or access rights*). |
| Menu Managers cannot see Menu Management | They also need access to the Settings app (*Administration: Access Rights*). |
| A menu is visible in one company and not another | Expected with company rules; check the active companies in the switcher. |
| Star or history icon missing in the top bar | Switch on *Favorite Menus* / *Recent Menus* for the user, then reload the page. |
| A favorite does not appear | Favorites only list menus the user can open now (rules, companies, parent menus, access rights). Sections without an action cannot be favorites; applications can. |
| *My Menus* is missing from the user menu | The user needs *Hide Menus Through Preferences*; reload after it is switched on. |
| Users can still open a hidden screen from a link | Expected: hiding a menu is not access control. Use access rights / record rules. |
| Locked out of Settings | Not possible for Settings administrators/Menu Managers (protected menus). For other users, open `/odoo/menu-management` as an administrator and remove the rule. |
| Emergency reset | As administrator: *Visibility Rules* › select all › Archive; or uninstall the module (no menu is modified). |

Server log: the module logs nothing during normal operation; access errors are logged by
Odoo as warnings (`Only menu administrators can ...`).

## Known limitations

* The **website** front-end application switcher (shown to logged-in users on website
  pages) uses Odoo's per-user cached `load_menus_root()`. There, company rules are
  evaluated against all the user's companies instead of only the active ones. All other
  rules apply normally, and the backend menu bar always follows the active companies.
* Changes apply at the next page load of each user (as for any Odoo menu change).
* Verified on Odoo 18.0 Community. The module only uses Community APIs and has no
  Enterprise dependency, but it has not been run on an Enterprise database by us.

## Support and license

Author and maintainer: **DevsCodeSpace**, <https://devscodespace.com>

License: GNU Lesser General Public License v3.0 (see `LICENSE`).

### Changelog

* **18.0.1.1.0**: application order (global and per user), favorite menus, recent menus,
  per-user Menu Management tab, copy menu settings.
* **18.0.1.0.0**: first release.
