# Copyright 2026 DevsCodeSpace (https://devscodespace.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from . import models
from . import wizard


def _dcs_uninstall_hook(env):
    """Drop every cached menu tree so no user keeps the restricted version."""
    env.registry.clear_cache()
