from __future__ import annotations

from .spell_resolution_attack import SpellResolutionAttackMixin
from .spell_resolution_common import SpellResolutionCommonMixin, SpellResolutionResult
from .spell_resolution_save import SpellResolutionSaveMixin


class SpellResolutionMixin(SpellResolutionAttackMixin, SpellResolutionSaveMixin, SpellResolutionCommonMixin):
    pass
