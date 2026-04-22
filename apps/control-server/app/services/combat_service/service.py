from .concentration import CombatConcentrationMixin
from .core import CombatCoreMixin
from .damage import CombatDamageMixin
from .dragonborn_breath import CombatDragonbornBreathMixin
from .effects import CombatEffectsMixin
from .entity_actions import CombatEntityActionMixin
from .entity_stats import CombatEntityStatsMixin
from .events import CombatEventsMixin
from .lifecycle import CombatLifecycleMixin
from .movement import CombatMovementMixin
from .npc_actions import CombatNpcActionMixin
from .player_death_save import CombatPlayerDeathSaveMixin
from .player_actions import CombatPlayerActionMixin
from .save_resolve import CombatSaveResolveMixin
from .spell_automation import CombatSpellAutomationMixin
from .spell_dice_math import CombatSpellDiceMathMixin
from .spell_lookup import CombatSpellLookupMixin
from .spells.cast_area_effect import CastAreaEffectMixin
from .spells.spell_resolution import SpellResolutionMixin
from .spells.spell_response import SpellResponseMixin
from .standard_actions import CombatStandardActionMixin
from .stat_lookup import CombatStatLookupMixin
from .status import CombatStatusMixin
from .weapon_resolution import CombatWeaponResolutionMixin


class CombatService(
    CombatEntityStatsMixin,
    CombatEventsMixin,
    CombatStatLookupMixin,
    CombatSpellLookupMixin,
    CombatCoreMixin,
    CombatMovementMixin,
    CombatEntityActionMixin,
    CombatStatusMixin,
    CombatLifecycleMixin,
    CombatDamageMixin,
    CombatSpellDiceMathMixin,
    CombatConcentrationMixin,
    CombatSpellAutomationMixin,
    SpellResolutionMixin,
    SpellResponseMixin,
    CastAreaEffectMixin,
    CombatWeaponResolutionMixin,
    CombatPlayerDeathSaveMixin,
    CombatPlayerActionMixin,
    CombatNpcActionMixin,
    CombatSaveResolveMixin,
    CombatEffectsMixin,
    CombatDragonbornBreathMixin,
    CombatStandardActionMixin,
):
    pass
