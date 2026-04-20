from __future__ import annotations

from app.services.roll_resolution import resolve_attack_base

from ..combat_targeting import get_combat_targeting_service
from .weapon_attack_damage import WeaponAttackDamageMixin
from .weapon_attack_roll import WeaponAttackRollMixin


class WeaponAttacksMixin(WeaponAttackRollMixin, WeaponAttackDamageMixin):
    pass
