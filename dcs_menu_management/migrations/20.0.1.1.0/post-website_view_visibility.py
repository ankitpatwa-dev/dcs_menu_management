# Copyright 2026 DevsCodeSpace (https://devscodespace.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
"""Remove the temporary database default set by the pre script."""


def migrate(cr, version):
    cr.execute("""
        SELECT column_default FROM information_schema.columns
         WHERE table_name = 'ir_ui_view' AND column_name = 'visibility'
    """)
    row = cr.fetchone()
    if row and row[0] is not None and 'public' in row[0]:
        cr.execute("ALTER TABLE ir_ui_view ALTER COLUMN visibility DROP DEFAULT")
