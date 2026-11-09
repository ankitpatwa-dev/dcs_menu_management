# Copyright 2026 DevsCodeSpace (https://devscodespace.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
"""Odoo 20: when Website is installed, ir_ui_view.visibility is NOT NULL with a
default that only exists in Python. During an upgrade, this module is loaded
before Website, so the views it adds in 1.1.0 would be inserted without that
column. Give the column its Website default for the duration of the upgrade;
the post script removes it again."""


def migrate(cr, version):
    cr.execute("""
        SELECT column_default FROM information_schema.columns
         WHERE table_name = 'ir_ui_view' AND column_name = 'visibility'
    """)
    row = cr.fetchone()
    if row and row[0] is None:
        cr.execute("ALTER TABLE ir_ui_view ALTER COLUMN visibility SET DEFAULT 'public'")
