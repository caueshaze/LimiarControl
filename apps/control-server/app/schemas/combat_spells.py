from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.campaign_entity_shared import AbilityName
from app.schemas.roll import RollResult, RollSource

from .combat_lifecycle import CombatActionCost


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
    target_ref_id: str | None = None
    origin_cell: "CombatGridCell | None" = None
    anchor_cell: "CombatGridCell | None" = None
    inventory_item_id: str | None = None
    spell_id: str | None = None
    spell_canonical_key: str | None = None
    campaign_spell_id: str | None = None
    spell_mode: (
        Literal["spell_attack", "saving_throw", "direct_damage", "heal", "utility"]
        | None
    ) = None
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


class CombatGridCell(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)


class CombatAreaTargetOutcome(BaseModel):
    target_ref_id: str
    target_display_name: str
    target_kind: Literal["player", "session_entity"]
    is_saved: bool | None = None
    roll: int | None = None
    roll_result: RollResult | None = None
    damage_applied: int | None = None
    healing_applied: int | None = None
    new_hp: int | None = None


class CombatMapPreviewToken(BaseModel):
    token_id: str
    label: str
    position: CombatGridCell
    combatant_id: str | None = None
    controller_type: str
    movement_speed_cells: int | None = None
    movement_budget: int | None = None


class CombatMapPreviewObstacle(BaseModel):
    cells: list[CombatGridCell] = Field(default_factory=list)
    blocks_movement: bool = False
    blocks_vision: bool = False
    blocks_effect: bool = False
    cover: str | None = None


class CombatMapPreviewState(BaseModel):
    session_id: str
    version: int
    grid_width: int
    grid_height: int
    tokens: list[CombatMapPreviewToken] = Field(default_factory=list)
    obstacles: list[CombatMapPreviewObstacle] = Field(default_factory=list)


class CombatMapEnsureResponse(BaseModel):
    session_id: str
    combat_phase: Literal["initiative", "placement", "active", "ended"]
    map_available: bool
    reason: str | None = None


class CombatAreaPreviewRequest(BaseModel):
    actor_participant_id: Optional[str] = None
    target_ref_id: str | None = None
    origin_cell: CombatGridCell
    anchor_cell: CombatGridCell
    inventory_item_id: str | None = None
    spell_id: str | None = None
    spell_canonical_key: str | None = None
    spell_mode: (
        Literal["spell_attack", "saving_throw", "direct_damage", "heal", "utility"]
        | None
    ) = None
    slot_level: Optional[int] = None


class CombatAreaPreviewResponse(BaseModel):
    is_valid: bool
    reason: str | None = None
    shape: Literal["sphere", "cone", "line"] | None = None
    affected_cells: list[CombatGridCell] = Field(default_factory=list)
    affected_target_ref_ids: list[str] = Field(default_factory=list)
    affected_token_ids: list[str] = Field(default_factory=list)
    map_version: int | None = None


class CombatMovementPreviewRequest(BaseModel):
    actor_participant_id: Optional[str] = None
    destination_cell: CombatGridCell


class CombatMovementPreviewResponse(BaseModel):
    is_valid: bool
    reason: str | None = None
    source_cell: CombatGridCell | None = None
    destination_cell: CombatGridCell
    path: list[CombatGridCell] = Field(default_factory=list)
    path_cost_units: int = Field(ge=0)
    movement_budget: int = Field(ge=0)
    movement_speed_cells: int = Field(ge=1)
    remaining_budget: int = Field(ge=0)
    map_version: int | None = None


class CombatSpellResult(BaseModel):
    spell_name: str
    spell_canonical_key: str | None = None
    action_kind: Literal[
        "spell_attack", "saving_throw", "direct_damage", "heal", "utility"
    ]
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
    pending_save_id: str | None = None
    effect_roll_required: bool = False
    effect_rolls: list[int] = Field(default_factory=list)
    base_effect: int | None = None
    effect_roll_source: RollSource | None = None
    action_cost: CombatActionCost | None = None
    summary_text: str | None = None
    inventory_refresh_required: bool = False
    concentration_check: "CombatConcentrationCheckResult | None" = None
    concentration_checks: list["CombatConcentrationCheckResult"] = Field(
        default_factory=list
    )
    area_shape: Literal["sphere", "cone", "line"] | None = None
    affected_target_ref_ids: list[str] = Field(default_factory=list)
    affected_cells: list[CombatGridCell] = Field(default_factory=list)
    area_target_outcomes: list[CombatAreaTargetOutcome] = Field(default_factory=list)
    target_count: int = 0
    elemental_affinity_eligible: bool = False
    elemental_affinity_damage_type: str | None = None
    elemental_affinity_bonus: int | None = None
