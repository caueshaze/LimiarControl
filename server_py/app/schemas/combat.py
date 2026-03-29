from typing import Literal, Optional

from pydantic import BaseModel, Field
from app.schemas.campaign_entity_shared import AbilityName
from app.schemas.roll import RollResult, RollSource

CombatActionCost = Literal["action", "bonus_action", "reaction", "free"]


class CombatParticipant(BaseModel):
    id: str
    kind: Literal["player", "session_entity"]
    ref_id: str
    display_name: str
    initiative: Optional[int] = None
    status: Literal["active", "downed", "stable", "dead", "defeated"] = "active"
    team: Literal["players", "enemies", "allies", "neutral"] = "neutral"
    visible: bool = True
    actor_user_id: Optional[str] = None  # Original actor if player
    active_effects: list[dict] = Field(default_factory=list)
    turn_resources: dict = Field(default_factory=lambda: {
        "action_used": False,
        "bonus_action_used": False,
        "reaction_used": False,
    })


class CombatStartRequest(BaseModel):
    participants: list[CombatParticipant]


class CombatSetInitiativeParticipant(BaseModel):
    id: str
    initiative: int


class CombatSetInitiativeRequest(BaseModel):
    initiatives: list[CombatSetInitiativeParticipant]


class CombatNextTurnRequest(BaseModel):
    actor_participant_id: Optional[str] = None


class CombatAttackRequest(BaseModel):
    actor_participant_id: Optional[str] = None
    target_ref_id: str
    weapon_item_id: Optional[str] = None
    has_advantage: bool = False
    has_disadvantage: bool = False
    roll_source: RollSource = "system"
    manual_roll: int | None = Field(default=None, ge=1, le=20)
    manual_rolls: list[int] | None = None
    override_resource_limit: bool = False


class CombatAttackResult(BaseModel):
    roll: int
    is_hit: bool
    damage: int
    is_critical: bool
    new_hp: Optional[int] = None
    roll_result: RollResult
    target_ac: int
    target_display_name: str
    target_kind: Literal["player", "session_entity"]
    weapon_name: str
    damage_dice: str
    damage_bonus: int
    attack_bonus: int
    damage_type: Optional[str] = None
    pending_attack_id: str | None = None
    damage_roll_required: bool = False
    damage_rolls: list[int] = Field(default_factory=list)
    base_damage: int | None = None
    damage_roll_source: RollSource | None = None
    concentration_check: "CombatConcentrationCheckResult | None" = None


class CombatCastSpellRequest(BaseModel):
    actor_participant_id: Optional[str] = None
    target_ref_id: str
    inventory_item_id: str | None = None
    spell_id: str | None = None
    spell_canonical_key: str | None = None
    spell_mode: Literal["spell_attack", "saving_throw", "direct_damage", "heal", "utility"] | None = None
    slot_level: Optional[int] = None
    has_advantage: bool = False
    has_disadvantage: bool = False
    roll_source: RollSource = "system"
    manual_roll: int | None = Field(default=None, ge=1, le=20)
    manual_rolls: list[int] | None = None
    dice_expression: Optional[str] = None
    is_heal: bool = False
    is_attack: bool = False
    damage_dice: str | None = None
    damage_bonus: int | None = None
    heal_dice: str | None = None
    heal_bonus: int | None = None
    damage_type: str | None = None
    save_ability: AbilityName | None = None
    save_dc: int | None = Field(default=None, ge=1)
    spell_attack_bonus: int | None = None
    concentration_roll_source: RollSource = "system"
    concentration_manual_roll: int | None = Field(default=None, ge=1, le=20)
    override_resource_limit: bool = False


class CombatSpellResult(BaseModel):
    spell_name: str
    spell_canonical_key: str | None = None
    action_kind: Literal["spell_attack", "saving_throw", "direct_damage", "heal", "utility"]
    effect_kind: Literal["damage", "healing"] | None = None
    damage: int = 0
    healing: int = 0
    damage_type: Optional[str] = None
    is_critical: Optional[bool] = None
    is_hit: Optional[bool] = None
    is_saved: Optional[bool] = None
    new_hp: Optional[int] = None
    roll: Optional[int] = None
    roll_result: RollResult | None = None
    target_ac: int | None = None
    target_display_name: str
    target_kind: Literal["player", "session_entity"]
    save_ability: AbilityName | None = None
    save_dc: int | None = None
    save_success_outcome: Literal["none", "half_damage"] | None = None
    effect_dice: str | None = None
    effect_bonus: int | None = None
    pending_spell_id: str | None = None
    effect_roll_required: bool = False
    effect_rolls: list[int] = Field(default_factory=list)
    base_effect: int | None = None
    effect_roll_source: RollSource | None = None
    action_cost: CombatActionCost | None = None
    summary_text: str | None = None
    inventory_refresh_required: bool = False
    concentration_check: "CombatConcentrationCheckResult | None" = None
    elemental_affinity_eligible: bool = False
    elemental_affinity_damage_type: str | None = None
    elemental_affinity_bonus: int | None = None


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
    action_kind: Literal["weapon_attack", "spell_attack", "saving_throw", "heal", "utility"]
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


# --- Active Effects ---

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
    "prone",
    "poisoned",
    "restrained",
    "blinded",
    "frightened",
    "charmed",
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


# --- Standard Actions ---

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
