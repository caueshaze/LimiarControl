from __future__ import annotations

from datetime import datetime, timezone
import random
from math import floor
from typing import Any
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

from app.core.config import settings
from app.integrations import LimiarMapClient, LimiarMapClientError
from app.models.base_item import BaseItemKind, BaseItemWeaponRangeType
from app.models.campaign import Campaign, SystemType
from app.models.campaign_member import CampaignMember
from app.models.combat import CombatPhase, CombatState
from app.models.session import Session as CampaignSession
from app.models.session_entity import SessionEntity
from app.models.session_state import SessionState
from app.models.campaign_entity import CampaignEntity
from app.models.inventory import InventoryItem
from app.models.item import Item, ItemType
from app.schemas.combat import (
    CombatApplyDamageRequest,
    CombatApplyHealingRequest,
    CombatAreaPreviewRequest,
    CombatAttackRequest,
    CombatCastSpellRequest,
    CombatEntityActionRequest,
    CombatMapPreviewState,
    CombatResolveDamageRequest,
    CombatResolveSpellEffectRequest,
    CombatSetInitiativeRequest,
    CombatStartRequest,
)
from app.schemas.campaign_entity import (
    SKILL_ABILITY_MAP,
    CombatAction,
    ability_modifier as derive_ability_modifier,
    resolve_initiative_bonus as resolve_entity_initiative_bonus,
    resolve_saving_throw_bonus as resolve_entity_saving_throw_bonus,
    resolve_skill_bonus as resolve_entity_skill_bonus,
)
from app.services.base_items import get_base_item_by_canonical_key
from app.services.base_spells import get_base_spell_by_canonical_key
from app.services.centrifugo import centrifugo
from app.services.draconic_ancestry import resolve_elemental_affinity
from app.services.magic_item_effects import (
    consume_inventory_item_charge,
    get_magic_item_effect,
    get_inventory_item_charges_current,
    get_magic_item_spell_key,
)
from app.services.realtime import build_event, campaign_channel, event_version, session_channel
from app.services.session_state_finalize import finalize_session_state_data
from app.services.roll_resolution import resolve_attack_base, resolve_saving_throw
from app.schemas.roll import RollActorStats, RollResult

from .combat_targeting import get_combat_targeting_service
from .exceptions import CombatServiceError, _parse_dice
from .targeting_requirements import (
    resolve_spell_targeting_requirements,
    resolve_weapon_targeting_requirements,
)
from .targeting_intent import AreaTargetingIntent, SpellCastIntent, WeaponAttackIntent
from .unit_conversion import meters_to_cells




from .actions.weapon_attacks import WeaponAttacksMixin
from .actions.wild_shape import WildShapeMixin
from .spells.spell_context import SpellContextMixin
from .spells.area_targeting import AreaTargetingMixin
from .spells.cast_area import CastAreaMixin
from .spells.cast_target import CastTargetMixin

class CombatPlayerActionMixin(
    WeaponAttacksMixin,
    WildShapeMixin,
    SpellContextMixin,
    AreaTargetingMixin,
    CastAreaMixin,
    CastTargetMixin,
):
    pass
