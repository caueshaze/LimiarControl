from __future__ import annotations

from .effects_actions import CombatEffectsActionsMixin
from .effects_core import CombatEffectsCoreMixin


class CombatEffectsMixin(CombatEffectsActionsMixin, CombatEffectsCoreMixin):
    pass
