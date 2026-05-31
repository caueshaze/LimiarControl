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
from .spell_declarative_effects import CombatSpellDeclarativeEffectsMixin
from .spell_dice_math import CombatSpellDiceMathMixin
from .spell_lookup import CombatSpellLookupMixin
from .spells.cast_area_effect import CastAreaEffectMixin
from .spells.illusions import IllusionsMixin
from .spells.spell_resolution import SpellResolutionMixin
from .spells.spell_response import SpellResponseMixin
from .spells.automation._social_spells import SocialSpellsAutomationMixin
from .spells.automation._hunters_mark_inventory import HuntersMarkInventoryAutomationMixin
from .spells.automation._buffs_weapon import BuffsWeaponAutomationMixin
from .spells.automation._buffs_physical import BuffsPhysicalAutomationMixin
from .spells.automation._buffs_defense import BuffsDefenseAutomationMixin
from .spells.automation._restoration_spells import RestorationSpellsAutomationMixin
from .spells.automation._command import CommandAutomationMixin
from .spells.automation._chill_touch import ChillTouchAutomationMixin
from .spells.automation._spiritual_weapon import SpiritualWeaponAutomationMixin
from .spells.automation._cantrip_anchors import CantripAnchorsAutomationMixin
from .spells.automation._light import LightAutomationMixin
from .spells.automation._detection_spells import DetectionSpellsAutomationMixin
from .spells.automation._nature_cantrips import NatureCantripsAutomationMixin
from .spells.automation._produce_flame import ProduceFlameAutomationMixin
from .spells.automation._protection_sanctuary import ProtectionSanctuaryAutomationMixin
from .spells.automation._bond_spells import BondSpellsAutomationMixin
from .spells.automation._control_spells import ControlSpellsAutomationMixin
from .standard_actions import CombatStandardActionMixin
from .stat_lookup import CombatStatLookupMixin
from .status import CombatStatusMixin
from .target_creature_type import CombatTargetCreatureTypeMixin
from .weapon_resolution import CombatWeaponResolutionMixin


class CombatService(
    CombatEntityStatsMixin,
    CombatEventsMixin,
    CombatStatLookupMixin,
    CombatTargetCreatureTypeMixin,
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
    SocialSpellsAutomationMixin,
    HuntersMarkInventoryAutomationMixin,
    BuffsWeaponAutomationMixin,
    BuffsPhysicalAutomationMixin,
    BuffsDefenseAutomationMixin,
    RestorationSpellsAutomationMixin,
    CommandAutomationMixin,
    ChillTouchAutomationMixin,
    SpiritualWeaponAutomationMixin,
    CantripAnchorsAutomationMixin,
    LightAutomationMixin,
    DetectionSpellsAutomationMixin,
    NatureCantripsAutomationMixin,
    ProduceFlameAutomationMixin,
    ProtectionSanctuaryAutomationMixin,
    BondSpellsAutomationMixin,
    ControlSpellsAutomationMixin,
    CombatSpellDeclarativeEffectsMixin,
    SpellResolutionMixin,
    SpellResponseMixin,
    CastAreaEffectMixin,
    IllusionsMixin,
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
