from __future__ import annotations

from app.services.healing_consumables import (
    HealingConsumableError,
    build_consumable_used_payload,
    consume_inventory_item,
    publish_consumable_used_realtime,
    record_consumable_used_activity,
    resolve_healing_consumable,
    roll_healing_consumable,
)
from app.services.roll_resolution import resolve_saving_throw

from .standard_action_combat import CombatStandardCombatActionMixin
from .standard_action_object import CombatStandardObjectActionMixin


class CombatStandardActionMixin(CombatStandardCombatActionMixin, CombatStandardObjectActionMixin):
    pass
