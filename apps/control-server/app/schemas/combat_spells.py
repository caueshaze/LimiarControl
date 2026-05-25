from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import AliasChoices, BaseModel, Field

from app.schemas.campaign_entity_shared import AbilityName
from app.schemas.base_spell_effects import AttackAdvantageCondition
from app.schemas.base_spell import SpellVariantManualNote
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
    is_magical_damage: bool = False
    pending_attack_id: str | None = None
    damage_roll_required: bool = False
    damage_rolls: list[int] = Field(default_factory=list)
    base_damage: int | None = None
    damage_roll_source: RollSource | None = None
    concentration_check: "CombatConcentrationCheckResult | None" = None
    damage_breakdown: "WeaponDamageBreakdown | None" = None
    extra_damage_rolls: list[int] = Field(default_factory=list)
    extra_damage_label: str | None = None


class EffectInstanceTarget(BaseModel):
    instance_index: int = Field(ge=1)
    target_ref_id: str


class TargetVariantAssignment(BaseModel):
    target_participant_id: str
    variant_key: str


class CombatCastSpellRequest(BaseModel):
    actor_participant_id: Optional[str] = None
    target_ref_id: str | None = None
    target_ref_ids: list[str] | None = None
    reaction_trigger: str | None = Field(
        default=None,
        validation_alias=AliasChoices("reaction_trigger", "reactionTrigger"),
    )
    falling_target_ref_ids: list[str] | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "falling_target_ref_ids", "fallingTargetRefIds"
        ),
    )
    origin_cell: "CombatGridCell | None" = None
    anchor_cell: "CombatGridCell | None" = None
    inventory_item_id: str | None = None
    weapon_item_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("weapon_item_id", "weaponItemId"),
    )
    spell_id: str | None = None
    spell_canonical_key: str | None = None
    campaign_spell_id: str | None = None
    variant_key: str | None = None
    target_variant_assignments: list[TargetVariantAssignment] | None = None
    spell_mode: (
        Literal["spell_attack", "saving_throw", "direct_damage", "heal", "utility", "teleport"]
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
    effect_instance_targets: list[EffectInstanceTarget] | None = None


class CombatResolveSpellContextRequest(BaseModel):
    actor_participant_id: Optional[str] = None
    target_ref_id: str | None = None
    inventory_item_id: str | None = None
    spell_id: str | None = None
    spell_canonical_key: str | None = None
    campaign_spell_id: str | None = None
    variant_key: str | None = None
    target_variant_assignments: list[TargetVariantAssignment] | None = None
    spell_mode: (
        Literal["spell_attack", "saving_throw", "direct_damage", "heal", "utility", "teleport"]
        | None
    ) = None
    slot_level: Optional[int] = None
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


class CombatResolvedSpellContext(BaseModel):
    spell_id: str | None = None
    spell_canonical_key: str | None = None
    campaign_spell_id: str | None = None
    inventory_item_id: str | None = None
    spell_name: str
    spell_level: int
    slot_level: int | None = None
    max_targets: int | None = None
    base_max_targets: int | None = None
    target_type: str | None = None
    selection_type: str | None = None
    area_shape: Literal["sphere", "cone", "line", "cube", "cylinder"] | None = None
    area_size_meters: float | None = None
    range_meters: float | None = None
    resolution_type: Literal[
        "spell_attack", "saving_throw", "direct_damage", "heal", "utility", "teleport"
    ]
    requires_attack_roll: bool = False
    requires_saving_throw: bool = False
    requires_target_hearing: bool | None = None
    save_ability: AbilityName | None = None
    attack_miss_outcome: Literal["none", "half_damage"] | None = None
    damage_type: str | None = None
    damage_preview: str | None = None
    delayed_damage_preview: str | None = None
    attack_advantage_condition: AttackAdvantageCondition | None = None
    effect_instance_count: int = 1
    effect_instance_dice: str | None = None
    base_effect_instance_count: int | None = None
    upcast_applied: bool = False
    upcast_added_instances: int = 0
    upcast_instance_effect_dice: str | None = None
    cover_applies_to_save: str | None = None
    utility: dict[str, Any] | None = None
    throw_attack: dict[str, Any] | None = None
    variants: list["SpellVariantSummaryPayload"] | None = None
    selected_variant_key: str | None = None
    target_variant_assignments: list[TargetVariantAssignment] | None = None


class SpellVariantSummaryPayload(BaseModel):
    key: str
    label: str
    description: str | None = None
    manualNotes: list[SpellVariantManualNote] | None = None


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
    cover: str | None = None
    base_save_dc: int | None = None
    effective_save_dc: int | None = None
    cover_modifier: int = 0
    excluded_by_guardrail: bool = False
    guardrail_reason: str | None = None


class CombatAreaGuardrailOutcome(BaseModel):
    target_ref_id: str
    target_display_name: str
    target_kind: Literal["player", "session_entity"]
    excluded_by_guardrail: bool = True
    guardrail_reason: str


class AppliedDeclarativeEffectSummary(BaseModel):
    type: str
    params: dict = Field(default_factory=dict)
    observability: dict | None = None


class AppliedDeclarativeEffectsByTargetEntry(BaseModel):
    target_display_name: str
    target_participant_id: str | None = None
    target_ref_id: str | None = None
    variant_key: str | None = None
    variant_label: str | None = None
    effects: list[AppliedDeclarativeEffectSummary] = Field(default_factory=list)


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


class CombatActiveAreaEffect(BaseModel):
    id: str
    source_spell_canonical_key: str | None = None
    source_spell_name: str
    caster_participant_id: str
    caster_ref_id: str | None = None
    caster_character_id: str | None = None
    origin_point: CombatGridCell
    anchor_cell: CombatGridCell
    area_shape: Literal["sphere", "cone", "line", "cube", "cylinder"]
    size_meters: float
    radius_meters: float | None = None
    length_meters: float | None = None
    side_meters: float | None = None
    affected_cells: list[CombatGridCell] = Field(default_factory=list)
    effect_kind: str
    duration: str | None = None
    concentration_owner_participant_id: str | None = None
    concentration_owner_ref_id: str | None = None
    created_round: int | None = None
    created_turn_index: int | None = None
    obscurement: str | None = None
    terrain_effect: str | None = None
    movement_damage_dice: str | None = None
    damage_type: str | None = None
    damage_per_meters: float | None = None


class CombatSpellAnchorMovement(BaseModel):
    max_meters_per_follow_up: float | None = None


class CombatSpellAnchor(BaseModel):
    id: str
    source_spell_key: str
    source_spell_name: str | None = None
    owner_participant_id: str
    created_by_participant_id: str
    position: CombatGridCell
    duration_type: Literal["rounds"]
    remaining_rounds: int | None = None
    expires_on: Literal["turn_start", "turn_end"] | None = None
    expires_at_participant_id: str | None = None
    render_kind: str = "generic"
    movement: CombatSpellAnchorMovement | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CombatMapPreviewState(BaseModel):
    session_id: str
    version: int
    grid_width: int
    grid_height: int
    tokens: list[CombatMapPreviewToken] = Field(default_factory=list)
    obstacles: list[CombatMapPreviewObstacle] = Field(default_factory=list)
    active_area_effects: list[CombatActiveAreaEffect] = Field(default_factory=list)
    spell_anchors: list[CombatSpellAnchor] = Field(default_factory=list)


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


class AreaPreviewAffectedTargetSpatialMetadata(BaseModel):
    target_ref_id: str
    target_display_name: str | None = None
    cover: str | None = None
    base_save_dc: int | None = None
    effective_save_dc: int | None = None
    cover_modifier: int = 0


class CombatAreaPreviewResponse(BaseModel):
    is_valid: bool
    reason: str | None = None
    shape: Literal["sphere", "cone", "line", "cube", "cylinder"] | None = None
    affected_cells: list[CombatGridCell] = Field(default_factory=list)
    affected_target_ref_ids: list[str] = Field(default_factory=list)
    affected_token_ids: list[str] = Field(default_factory=list)
    map_version: int | None = None
    affected_target_spatial_metadata: list[AreaPreviewAffectedTargetSpatialMetadata] = Field(
        default_factory=list
    )
    guardrail_target_outcomes: list[CombatAreaGuardrailOutcome] = Field(
        default_factory=list
    )


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
    fall_result: dict[str, Any] | None = None
    source_elevation_meters: float | None = None
    destination_elevation_meters: float | None = None


class EffectInstanceOutcome(BaseModel):
    instance_index: int
    target_ref_id: str
    target_display_name: str
    target_kind: Literal["player", "session_entity"]
    damage: int = 0
    healing: int = 0
    is_hit: bool | None = None
    is_saved: bool | None = None
    is_critical: bool = False
    roll: int | None = None
    roll_result: RollResult | None = None
    new_hp: int | None = None
    cover: str | None = None
    base_ac: int | None = None
    effective_ac: int | None = None
    cover_modifier: int = 0


class CombatSpellResult(BaseModel):
    spell_name: str
    spell_canonical_key: str | None = None
    selected_variant_key: str | None = None
    selected_variant_label: str | None = None
    context_origin: Literal["initial_cast", "pending_save", "pending_spell"] | None = None
    concentration_group: str | None = None
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
    cover: str | None = None
    base_ac: int | None = None
    base_save_dc: int | None = None
    cover_modifier: int = 0
    target_display_name: str
    target_kind: Literal["player", "session_entity"]
    save_ability: AbilityName | None = None
    # Effective DC after cover modifier (cover already factored in at response time).
    # Area spells expose per-target base_save_dc + effective_save_dc via CombatAreaTargetOutcome.
    save_dc: int | None = None
    save_success_outcome: Literal["none", "half_damage"] | None = None
    attack_miss_outcome: Literal["none", "half_damage"] | None = None
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
    area_shape: Literal["sphere", "cone", "line", "cube", "cylinder"] | None = None
    affected_target_ref_ids: list[str] = Field(default_factory=list)
    affected_cells: list[CombatGridCell] = Field(default_factory=list)
    area_target_outcomes: list[CombatAreaTargetOutcome] = Field(default_factory=list)
    target_count: int = 0
    active_area_effect: CombatActiveAreaEffect | None = None
    elemental_affinity_eligible: bool = False
    elemental_affinity_damage_type: str | None = None
    elemental_affinity_bonus: int | None = None
    effect_instance_count: int | None = None
    effect_instance_dice: str | None = None
    base_effect_instance_count: int | None = None
    effect_instance_outcomes: list[EffectInstanceOutcome] = Field(default_factory=list)
    target_variant_assignments: list[dict] | None = None
    manual_notes_by_target: list[dict] | None = None
    applied_declarative_effects_by_target: list[AppliedDeclarativeEffectsByTargetEntry] | None = None
    damage_mode: Literal["normal", "half_on_miss"] = "normal"
