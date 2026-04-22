from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.campaign_entity_shared import AbilityName
from app.schemas.roll import RollResult, RollSource

from .combat_lifecycle import CombatActionCost
from .combat_spells import CombatGridCell


class CombatEntityActionRequest(BaseModel):
    actor_participant_id: Optional[str] = None
    target_ref_id: Optional[str] = None
    combat_action_id: str
    has_advantage: bool = False
    has_disadvantage: bool = False
    roll_source: RollSource = "system"
    manual_roll: int | None = Field(default=None, ge=1, le=20)
    manual_rolls: list[int] | None = None
    concentration_roll_source: RollSource = "system"
    concentration_manual_roll: int | None = Field(default=None, ge=1, le=20)
    override_resource_limit: bool = False


class CombatEntityActionResult(BaseModel):
    action_name: str
    action_kind: Literal[
        "weapon_attack", "spell_attack", "saving_throw", "heal", "utility"
    ]
    damage: int = 0
    damage_type: Optional[str] = None
    healing: int = 0
    is_critical: Optional[bool] = None
    is_hit: Optional[bool] = None
    is_saved: Optional[bool] = None
    new_hp: Optional[int] = None
    roll: Optional[int] = None
    save_dc: Optional[int] = None
    save_roll: Optional[int] = None
    save_success_outcome: Literal["none", "half_damage"] | None = None
    roll_result: RollResult | None = None
    target_ac: int | None = None
    target_display_name: str | None = None
    damage_dice: str | None = None
    damage_bonus: int | None = None
    attack_bonus: int | None = None
    pending_attack_id: str | None = None
    pending_save_id: str | None = None
    damage_roll_required: bool = False
    damage_rolls: list[int] = Field(default_factory=list)
    base_damage: int | None = None
    damage_roll_source: RollSource | None = None
    concentration_check: "CombatConcentrationCheckResult | None" = None


class CombatConcentrationCheckResult(BaseModel):
    actor_participant_id: str | None = None
    actor_display_name: str
    damage_taken: int
    dc: int
    success: bool
    roll_result: RollResult
    broken_effect_labels: list[str] = Field(default_factory=list)
    source_spell_keys: list[str] = Field(default_factory=list)
    summary_text: str


class CombatResolveDamageRequest(BaseModel):
    actor_participant_id: Optional[str] = None
    pending_attack_id: str
    roll_source: RollSource = "system"
    manual_rolls: list[int] | None = None
    concentration_roll_source: RollSource = "system"
    concentration_manual_roll: int | None = Field(default=None, ge=1, le=20)


class CombatResolveSpellEffectRequest(BaseModel):
    actor_participant_id: Optional[str] = None
    pending_spell_id: str
    roll_source: RollSource = "system"
    manual_rolls: list[int] | None = None
    concentration_roll_source: RollSource = "system"
    concentration_manual_roll: int | None = Field(default=None, ge=1, le=20)


class CombatApplyDamageRequest(BaseModel):
    target_ref_id: str
    amount: int
    kind: Literal["player", "session_entity"]
    type_override: Optional[str] = None
    concentration_roll_source: RollSource = "system"
    concentration_manual_roll: int | None = Field(default=None, ge=1, le=20)


class CombatApplyHealingRequest(BaseModel):
    target_ref_id: str
    amount: int
    kind: Literal["player", "session_entity"]


class CombatDeathSaveRequest(BaseModel):
    actor_participant_id: Optional[str] = None


class CombatReviveRequest(BaseModel):
    target_participant_id: str
    hp: int | None = Field(default=1, ge=1)


class CombatReviveResult(BaseModel):
    new_hp: int
    status: Literal["active"]


ActiveEffectKind = Literal[
    "condition",
    "temp_ac_bonus",
    "attack_bonus",
    "damage_bonus",
    "advantage_on_attacks",
    "disadvantage_on_attacks",
    "dodging",
    "hidden",
    "spell_effect",
]

ActiveEffectConditionType = Literal[
    "blinded",
    "charmed",
    "deafened",
    "frightened",
    "grappled",
    "incapacitated",
    "invisible",
    "paralyzed",
    "petrified",
    "poisoned",
    "prone",
    "restrained",
    "stunned",
    "unconscious",
]

ActiveEffectDurationType = Literal[
    "manual",
    "rounds",
    "until_turn_start",
    "until_turn_end",
]


class ActiveEffect(BaseModel):
    id: str
    source_participant_id: Optional[str] = None
    kind: ActiveEffectKind
    condition_type: Optional[ActiveEffectConditionType] = None
    numeric_value: Optional[int] = None
    duration_type: ActiveEffectDurationType = "manual"
    remaining_rounds: Optional[int] = None
    expires_on: Optional[Literal["turn_start", "turn_end"]] = None
    expires_at_participant_id: Optional[str] = None
    created_at: str
    metadata: dict | None = None
    display_label: str | None = None


class CombatApplyEffectRequest(BaseModel):
    target_participant_id: str
    kind: ActiveEffectKind
    condition_type: Optional[ActiveEffectConditionType] = None
    numeric_value: Optional[int] = None
    duration_type: ActiveEffectDurationType = "manual"
    remaining_rounds: Optional[int] = Field(default=None, ge=1)
    expires_at_participant_id: Optional[str] = None
    source_participant_id: Optional[str] = None
    metadata: dict | None = None
    display_label: str | None = None


class CombatRemoveEffectRequest(BaseModel):
    target_participant_id: str
    effect_id: str


class CombatConsumeReactionRequest(BaseModel):
    participant_id: str
    override_resource_limit: bool = False


class CombatReactionRequestRequest(BaseModel):
    actor_participant_id: str


class CombatReactionResolveRequest(BaseModel):
    actor_participant_id: str
    decision: Literal["approve", "deny"]
    override_resource_limit: bool = False


class CombatResolveSaveRequest(BaseModel):
    target_participant_id: str
    pending_save_id: str
    roll_source: RollSource = "system"
    manual_roll: int | None = Field(default=None, ge=1, le=20)
    manual_rolls: list[int] | None = None


StandardActionType = Literal[
    "dodge",
    "help",
    "hide",
    "use_object",
    "dash",
    "disengage",
    "dragonborn_breath_weapon",
]


class CombatStandardActionRequest(BaseModel):
    action: StandardActionType
    actor_participant_id: Optional[str] = None
    target_participant_id: Optional[str] = None
    inventory_item_id: Optional[str] = None
    description: Optional[str] = None
    roll_source: RollSource = "system"
    manual_roll: int | None = Field(default=None, ge=1, le=20)
    manual_rolls: list[int] | None = None
    override_resource_limit: bool = False


class CombatWildShapeAttackRequest(BaseModel):
    actor_participant_id: Optional[str] = None
    target_ref_id: str
    attack_index: int = 0
    has_advantage: bool = False
    has_disadvantage: bool = False
    roll_source: RollSource = "system"
    manual_roll: int | None = Field(default=None, ge=1, le=20)
    manual_rolls: list[int] | None = None
    override_resource_limit: bool = False


class CombatStandardActionResult(BaseModel):
    action: StandardActionType
    actor_name: str
    message: str
    roll_result: RollResult | None = None
    effect_applied: bool = False
    target_display_name: str | None = None
    target_kind: Literal["player", "session_entity"] | None = None
    healing: int | None = None
    damage: int | None = None
    damage_type: str | None = None
    new_hp: int | None = None
    save_ability: AbilityName | None = None
    save_dc: int | None = None
    is_saved: bool | None = None
    save_success_outcome: Literal["none", "half_damage"] | None = None
    effect_dice: str | None = None
    effect_rolls: list[int] = Field(default_factory=list)
    effect_roll_source: RollSource | None = None
    uses_remaining: int | None = None
    concentration_check: CombatConcentrationCheckResult | None = None
