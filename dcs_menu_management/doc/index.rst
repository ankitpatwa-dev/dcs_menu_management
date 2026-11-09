========================
Advanced Menu Management
========================

Odoo 20.0 · Community and Enterprise · LGPL-3 · by DevsCodeSpace (https://devscodespace.com)

Decide who sees which Odoo menu without editing XML, Python or security groups. The module
only narrows Odoo's standard menu visibility: it never shows a menu, an action or a record
to someone Odoo would not show it to.

Installation
============

1. Copy ``dcs_menu_management`` into an addons path and restart Odoo.
2. Developer mode › Apps › Update Apps List.
3. Search *Advanced Menu Management* and click **Activate**.

The module only depends on the standard ``web`` module.

Who can configure
=================

* Settings administrators.
* Users in the **Menu Manager** group (user form, *Menu Management* section). They also need
  access to the Settings app (*Administration: Access Rights*).

Hide a menu for everyone
========================

1. Settings › Menu Management › **Menu Configuration**.
2. Find the menu (expand the application or use the search box).
3. Click the eye-slash button. Click the eye button to restore it.

Restrict a menu
===============

Click the sliders button of a menu to open its rule:

* **Users**: *Hide for Users*, *Show Only for Users*.
* **Companies**: *Hide for Companies*, *Show Only for Companies* (active companies of the
  company switcher; with several active companies the menu stays visible if one allows it).
* **Security Groups**: *Show Only for Groups*, *Hide for Groups* (on top of the menu's own
  Odoo groups, which are never changed).

Archive a rule to suspend it; *All Menus* › **Remove Restrictions** deletes it.

Preview as user
===============

In Menu Configuration, choose a user (and their active companies) under **Preview as user**.
Every menu shows *Visible* or why it is hidden.

Personal menus
==============

Administrators switch on **Hide Menus Through Preferences** for selected users
(Settings › Menu Management › Personal Preferences, or the user form › *Menu Visibility*).

Those users open their avatar menu › **My Menus**, switch on the menus to hide and click
**Save and Reload**. They can bring menus back the same way or from *My Preferences* › *My Menus*.
Personal choices only affect that user.

Application order
=================

* Everyone: Settings › Menu Management › **Application Order**; drag, then **Save and Reload**.
* One user: user form › *Menu Management* tab › **Application Order**.
* Users allowed to customise their menus: *My Menus* › **Reorder My Apps**.

Odoo's own menu sequence is never changed.

Favorite and recent menus
=========================

Switch on **Favorite Menus** and **Recent Menus** for a user (user form › *Menu Management*, or
Settings › Menu Management › **User Menu Settings**). The user then has a star (favorites: add
the current menu, open, remove with ×) and a history icon (last 10 menus opened) in the top bar.
Only menus the user can open are ever listed. Recent menus are private to each user.

Copy menu settings
==================

User form › *Menu Management* › **Copy Menu Settings to Other Users**: hidden menus, personal
hidden menus, favorites, application order and options.

How visibility is decided
=========================

A menu is shown only if all of these allow it:

1. Odoo's standard visibility (menu groups, model access, debug-only menus);
2. protected menus: Settings and Menu Management always stay visible for menu administrators;
3. *Hide for Everyone*;
4. user lists;
5. company lists;
6. group lists;
7. the user's personal preferences;
8. hierarchy: a hidden menu hides its sub-menus, and a section whose items are all hidden
   disappears.

Security notes
==============

* Hiding a menu is not access control. Protect data with access rights and record rules.
* Rules are stored apart from menus: module upgrades keep them, uninstalling the module
  leaves every menu untouched.
* Nobody can change another user's personal menus except menu administrators.

Troubleshooting
===============

* Changes apply when the user reloads the page.
* If a menu stays hidden, use **Preview as user** to see the reason.
* A *Show Only* user who still does not see a menu lacks the menu's Odoo groups or access
  rights: rules never add visibility.
* The website front-end application switcher evaluates company rules against all the
  user's companies; the backend menu bar always follows the active companies.

Support
=======

DevsCodeSpace · https://devscodespace.com
