from .core import CombatCoreMixin
from .damage import CombatDamageMixin
from .effects import CombatEffectsMixin
from .entity_actions import CombatEntityActionMixin
from .entity_stats import CombatEntityStatsMixin
from .events import CombatEventsMixin
from .lifecycle import CombatLifecycleMixin
from .npc_actions import CombatNpcActionMixin
from .player_actions import CombatPlayerActionMixin
from .standard_actions import CombatStandardActionMixin
from .status import CombatStatusMixin


class CombatService(
    CombatEntityStatsMixin,
    CombatEventsMixin,
    CombatCoreMixin,
    CombatEntityActionMixin,
    CombatStatusMixin,
    CombatLifecycleMixin,
    CombatDamageMixin,
    CombatPlayerActionMixin,
    CombatNpcActionMixin,
    CombatEffectsMixin,
    CombatStandardActionMixin,
):
    pass
