from __future__ import annotations

from .damage_admin import CombatDamageAdminMixin
from .damage_core import CombatDamageCoreMixin


class CombatDamageMixin(CombatDamageAdminMixin, CombatDamageCoreMixin):
    pass
