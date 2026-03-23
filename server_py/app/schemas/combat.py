from typing import Literal, Optional

from pydantic import BaseModel, Field
from app.schemas.campaign_entity_shared import AbilityName
from app.schemas.roll import RollResult, RollSource


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


class CombatCastSpellRequest(BaseModel):
    actor_participant_id: Optional[str] = None
    target_ref_id: str
    spell_id: str | None = None
    spell_canonical_key: str | None = None
    spell_mode: Literal["spell_attack", "saving_throw", "direct_damage", "heal"] | None = None
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


class CombatSpellResult(BaseModel):
    spell_name: str
    spell_canonical_key: str | None = None
    action_kind: Literal["spell_attack", "saving_throw", "direct_damage", "heal"]
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
    effect_dice: str | None = None
    effect_bonus: int | None = None
    pending_spell_id: str | None = None
    effect_roll_required: bool = False
    effect_rolls: list[int] = Field(default_factory=list)
    base_effect: int | None = None
    effect_roll_source: RollSource | None = None


class CombatEntityActionRequest(BaseModel):
    actor_participant_id: Optional[str] = None
    target_ref_id: Optional[str] = None
    combat_action_id: str
    has_advantage: bool = False
    has_disadvantage: bool = False
    roll_source: RollSource = "system"
    manual_roll: int | None = Field(default=None, ge=1, le=20)
    manual_rolls: list[int] | None = None


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


class CombatResolveDamageRequest(BaseModel):
    actor_participant_id: Optional[str] = None
    pending_attack_id: str
    roll_source: RollSource = "system"
    manual_rolls: list[int] | None = None


class CombatResolveSpellEffectRequest(BaseModel):
    actor_participant_id: Optional[str] = None
    pending_spell_id: str
    roll_source: RollSource = "system"
    manual_rolls: list[int] | None = None


class CombatApplyDamageRequest(BaseModel):
    target_ref_id: str
    amount: int
    kind: Literal["player", "session_entity"]
    type_override: Optional[str] = None


class CombatApplyHealingRequest(BaseModel):
    target_ref_id: str
    amount: int
    kind: Literal["player", "session_entity"]


class CombatDeathSaveRequest(BaseModel):
    actor_participant_id: Optional[str] = None
