import type {
  RollResult,
  RollSource
} from "../../entities/roll/rollResolution.types";
import type { SpellVariantManualNote } from "../../entities/base-spell";
import { http } from "./http";

export type CombatPhase = "initiative" | "placement" | "active" | "ended";
export type CombatParticipantKind = "player" | "session_entity";
export type CombatSpellMode =
  | "spell_attack"
  | "saving_throw"
  | "direct_damage"
  | "heal"
  | "utility";
export type CombatActionCost = "action" | "bonus_action" | "reaction" | "free";

// --- Active Effects ---

export type ActiveEffectKind =
  | "condition"
  | "temp_ac_bonus"
  | "attack_bonus"
  | "damage_bonus"
  | "advantage_on_attacks"
  | "disadvantage_on_attacks"
  | "dodging"
  | "hidden"
  | "spell_effect";

export type ActiveEffectConditionType =
  | "prone"
  | "poisoned"
  | "restrained"
  | "blinded"
  | "frightened"
  | "charmed"
  | "hostile_to_caster";

export type ActiveEffectDurationType =
  | "manual"
  | "rounds"
  | "until_turn_start"
  | "until_turn_end"
  | "until_long_rest"
  | "until_short_rest"
  | "until_removed"
  | "timed";

export type ActiveEffect = {
  id: string;
  source_participant_id?: string | null;
  kind: ActiveEffectKind;
  condition_type?: ActiveEffectConditionType | null;
  numeric_value?: number | null;
  duration_type: ActiveEffectDurationType;
  remaining_rounds?: number | null;
  expires_on?: "turn_start" | "turn_end" | null;
  expires_at_participant_id?: string | null;
  created_at_game_time_seconds?: number | null;
  expires_at_game_time_seconds?: number | null;
  created_at: string;
  metadata?: Record<string, unknown> | null;
  display_label?: string | null;
};

export type PendingSpellPreparation = {
  source: string;
  classKey: string;
  preparedLimit: number;
  currentPreparedSpellIds: string[];
  createdAt: string;
  availableDuringRest: boolean;
};

export type CombatSpellContextOrigin =
  | "initial_cast"
  | "pending_save"
  | "pending_spell";

export type AppliedDeclarativeEffectSummary = {
  type?: string | null;
  params?: Record<string, unknown> | null;
  observability?: {
    rolled_temp_hp?: number | null;
    applied_temp_hp?: boolean | null;
    previous_temp_hp?: number | null;
    final_temp_hp?: number | null;
    does_not_expire_temp_hp?: boolean | null;
  } | null;
};

export type AppliedDeclarativeEffectsByTargetEntry = {
  target_display_name: string;
  target_participant_id?: string | null;
  target_ref_id?: string | null;
  variant_key?: string | null;
  variant_label?: string | null;
  effects: AppliedDeclarativeEffectSummary[];
};

export type TurnResources = {
  action_used: boolean;
  bonus_action_used: boolean;
  reaction_used: boolean;
};

export type ReactionRequestState = {
  status: "pending" | "approved" | "denied";
  requested_at: string;
};

export type PendingSave = {
  id: string;
  status: "pending";
  spell_name: string;
  spell_canonical_key?: string | null;
  attacker_display_name?: string | null;
  save_ability: string;
  save_dc: number;
  effect_kind?: "damage" | "healing" | null;
  selected_variant_key?: string | null;
  selected_variant_label?: string | null;
  context_origin?: CombatSpellContextOrigin | null;
  concentration_group?: string | null;
  target_variant_assignments?: Array<{
    target_participant_id?: string | null;
    target_ref_id?: string | null;
    variant_key: string;
    variant_label?: string | null;
  }> | null;
  manual_notes_by_target?: Array<{
    target_participant_id?: string | null;
    target_ref_id?: string | null;
    target_display_name: string;
    variant_key: string;
    variant_label?: string | null;
    manual_notes: SpellVariantManualNote[];
  }> | null;
};

export type SaveResolution = {
  spell_name: string;
  pending_save_id?: string | null;
  target_display_name: string;
  save_ability: string;
  save_dc: number;
  is_saved: boolean;
  roll_total: number;
  damage: number;
  healing: number;
  damage_type?: string | null;
  effect_kind?: "damage" | "healing" | null;
  new_hp?: number | null;
  roll_result: RollResult;
  pending_spell_id?: string | null;
  selected_variant_key?: string | null;
  selected_variant_label?: string | null;
  context_origin?: CombatSpellContextOrigin | null;
  concentration_group?: string | null;
  target_variant_assignments?: Array<{
    target_participant_id?: string | null;
    target_ref_id?: string | null;
    variant_key: string;
    variant_label?: string | null;
  }> | null;
  manual_notes_by_target?: Array<{
    target_participant_id?: string | null;
    target_ref_id?: string | null;
    target_display_name: string;
    variant_key: string;
    variant_label?: string | null;
    manual_notes: SpellVariantManualNote[];
  }> | null;
  applied_declarative_effects_by_target?: AppliedDeclarativeEffectsByTargetEntry[] | null;
};

export type CombatParticipant = {
  id: string;
  kind: "player" | "session_entity";
  ref_id: string;
  display_name: string;
  initiative: number | null;
  status: "active" | "downed" | "stable" | "dead" | "defeated";
  team: "players" | "enemies" | "allies" | "neutral";
  visible: boolean;
  actor_user_id: string | null;
  active_effects?: ActiveEffect[];
  turn_resources?: TurnResources;
  reaction_request?: ReactionRequestState;
  pending_save?: PendingSave;
  last_save_resolution?: SaveResolution;
};

export type CombatState = {
  id: string;
  session_id: string;
  phase: CombatPhase;
  round: number;
  current_turn_index: number;
  participants: CombatParticipant[];
  use_map: boolean;
  local_distances: Record<string, Record<string, number>>;
  active_area_effects?: CombatActiveAreaEffect[];
  spell_anchors?: CombatSpellAnchor[];
  created_at: string;
  updated_at?: string | null;
};

export type CombatLocalDistanceEntry = {
  from_ref_id: string;
  to_ref_id: string;
  distance_meters: number;
};

export type CombatUpdateDistancesRequest = {
  distances: CombatLocalDistanceEntry[];
};

export type CombatMapChoiceKind = "campaign_map" | "demo_map";

export type CombatStartRequest = {
  participants: CombatParticipant[];
  selectedMap?: {
    kind: CombatMapChoiceKind;
    mapId?: string | null;
  } | null;
};

export type CombatSetInitiativeParticipant = {
  id: string;
  initiative: number;
};

export type CombatSetInitiativeRequest = {
  initiatives: CombatSetInitiativeParticipant[];
};

export type CombatNextTurnRequest = {
  actor_participant_id?: string | null;
};

export type CombatReviveRequest = {
  target_participant_id: string;
  hp?: number | null;
};

export type CombatReviveResult = {
  new_hp: number;
  status: "active";
};

export type CombatAttackRequest = {
  actor_participant_id?: string | null;
  target_ref_id: string;
  weapon_item_id?: string | null;
  has_advantage?: boolean;
  has_disadvantage?: boolean;
  roll_source?: RollSource;
  manual_roll?: number | null;
  manual_rolls?: [number, number] | null;
  override_resource_limit?: boolean;
};

export type CombatAttackResult = {
  roll: number;
  is_hit: boolean;
  damage: number;
  is_critical: boolean;
  new_hp: number | null;
  roll_result: RollResult;
  target_ac: number;
  target_display_name: string;
  target_kind: CombatParticipantKind;
  weapon_name: string;
  damage_dice: string;
  damage_bonus: number;
  attack_bonus: number;
  damage_type?: string | null;
  pending_attack_id?: string | null;
  damage_roll_required?: boolean;
  damage_rolls?: number[];
  base_damage?: number | null;
  damage_roll_source?: RollSource | null;
  concentration_check?: CombatConcentrationCheckResult | null;
};

export type CombatCastSpellRequest = {
  actor_participant_id?: string | null;
  target_ref_id?: string | null;
  target_ref_ids?: string[] | null;
  effect_instance_targets?: Array<{
    instance_index: number;
    target_ref_id: string;
  }> | null;
  origin_cell?: { x: number; y: number } | null;
  anchor_cell?: { x: number; y: number } | null;
  inventory_item_id?: string | null;
  spell_id?: string | null;
  spell_canonical_key?: string | null;
  campaign_spell_id?: string | null;
  variant_key?: string | null;
  target_variant_assignments?: Array<{
    target_participant_id: string;
    variant_key: string;
  }> | null;
  spell_mode?: CombatSpellMode | null;
  slot_level?: number | null;
  has_advantage?: boolean;
  has_disadvantage?: boolean;
  roll_source?: RollSource;
  manual_roll?: number | null;
  manual_rolls?: [number, number] | null;
  dice_expression?: string | null;
  is_heal?: boolean;
  is_attack?: boolean;
  damage_dice?: string | null;
  damage_bonus?: number | null;
  heal_dice?: string | null;
  heal_bonus?: number | null;
  damage_type?: string | null;
  save_ability?: string | null;
  save_dc?: number | null;
  spell_attack_bonus?: number | null;
  concentration_roll_source?: RollSource;
  concentration_manual_roll?: number | null;
  override_resource_limit?: boolean;
};

export type CombatResolveSpellContextRequest = {
  actor_participant_id?: string | null;
  target_ref_id?: string | null;
  inventory_item_id?: string | null;
  spell_id?: string | null;
  spell_canonical_key?: string | null;
  campaign_spell_id?: string | null;
  variant_key?: string | null;
  target_variant_assignments?: Array<{
    target_participant_id: string;
    variant_key: string;
  }> | null;
  spell_mode?: CombatSpellMode | null;
  slot_level?: number | null;
};

export type CombatResolvedSpellContext = {
  spell_id?: string | null;
  spell_canonical_key?: string | null;
  campaign_spell_id?: string | null;
  inventory_item_id?: string | null;
  spell_name: string;
  spell_level: number;
  slot_level?: number | null;
  max_targets?: number | null;
  base_max_targets?: number | null;
  target_type?: string | null;
  selection_type?: string | null;
  area_shape?: "sphere" | "cone" | "line" | "cube" | "cylinder" | null;
  area_size_meters?: number | null;
  range_meters?: number | null;
  resolution_type: CombatSpellMode;
  requires_attack_roll: boolean;
  requires_saving_throw: boolean;
  save_ability?: string | null;
  damage_type?: string | null;
  damage_preview?: string | null;
  effect_instance_count: number;
  effect_instance_dice?: string | null;
  base_effect_instance_count?: number | null;
  upcast_applied: boolean;
  upcast_added_instances: number;
  upcast_instance_effect_dice?: string | null;
  cover_applies_to_save?: string | null;
  variants?: Array<{
    key: string;
    label: string;
    description?: string | null;
    manualNotes?: SpellVariantManualNote[] | null;
  }> | null;
  selected_variant_key?: string | null;
  target_variant_assignments?: Array<{
    target_participant_id: string;
    variant_key: string;
  }> | null;
};

export type CombatSpellResult = {
  spell_name: string;
  spell_canonical_key?: string | null;
  selected_variant_key?: string | null;
  selected_variant_label?: string | null;
  context_origin?: CombatSpellContextOrigin | null;
  concentration_group?: string | null;
  action_kind: CombatSpellMode;
  effect_kind?: "damage" | "healing" | null;
  damage: number;
  healing: number;
  damage_type?: string | null;
  is_critical?: boolean | null;
  is_hit?: boolean | null;
  is_saved?: boolean | null;
  new_hp?: number | null;
  roll?: number | null;
  roll_result?: RollResult | null;
  target_ac?: number | null;
  cover?: string | null;
  base_ac?: number | null;
  base_save_dc?: number | null;
  cover_modifier?: number;
  target_display_name: string;
  target_kind: CombatParticipantKind;
  save_ability?: string | null;
  save_dc?: number | null;
  save_success_outcome?: "none" | "half_damage" | null;
  effect_dice?: string | null;
  effect_bonus?: number | null;
  pending_spell_id?: string | null;
  pending_save_id?: string | null;
  effect_roll_required?: boolean;
  effect_rolls?: number[];
  base_effect?: number | null;
  effect_roll_source?: RollSource | null;
  action_cost?: CombatActionCost | null;
  summary_text?: string | null;
  inventory_refresh_required?: boolean;
  concentration_check?: CombatConcentrationCheckResult | null;
  concentration_checks?: CombatConcentrationCheckResult[];
  area_shape?: "sphere" | "cone" | "line" | "cube" | "cylinder" | null;
  affected_target_ref_ids?: string[];
  affected_cells?: Array<{ x: number; y: number }>;
  area_target_outcomes?: Array<{
    target_ref_id: string;
    target_display_name: string;
    target_kind: CombatParticipantKind;
    is_saved?: boolean | null;
    roll?: number | null;
    roll_result?: RollResult | null;
    damage_applied?: number | null;
    healing_applied?: number | null;
    new_hp?: number | null;
    cover?: string | null;
    base_save_dc?: number | null;
    effective_save_dc?: number | null;
    cover_modifier?: number;
    excluded_by_guardrail?: boolean;
    guardrail_reason?: string | null;
  }>;
  effect_instance_outcomes?: Array<{
    instance_index: number;
    target_ref_id: string;
    target_display_name: string;
    target_kind: CombatParticipantKind;
    damage?: number;
    healing?: number;
    is_hit?: boolean | null;
    is_saved?: boolean | null;
    is_critical?: boolean;
    roll?: number | null;
    roll_result?: RollResult | null;
    new_hp?: number | null;
    cover?: string | null;
    base_ac?: number | null;
    effective_ac?: number | null;
    base_save_dc?: number | null;
    effective_save_dc?: number | null;
    cover_modifier?: number;
  }>;
  target_count?: number;
  elemental_affinity_eligible?: boolean;
  elemental_affinity_damage_type?: string | null;
  elemental_affinity_bonus?: number | null;
  effect_instance_count?: number | null;
  effect_instance_dice?: string | null;
  base_effect_instance_count?: number | null;
  target_variant_assignments?: Array<{
    target_ref_id?: string | null;
    target_participant_id?: string | null;
    variant_key: string;
    variant_label?: string | null;
  }> | null;
  manual_notes_by_target?: Array<{
    target_ref_id?: string | null;
    target_participant_id?: string | null;
    target_display_name: string;
    variant_key: string;
    variant_label?: string | null;
    manual_notes: SpellVariantManualNote[];
  }> | null;
  applied_declarative_effects_by_target?: AppliedDeclarativeEffectsByTargetEntry[] | null;
};

export type CombatMapPreviewToken = {
  token_id: string;
  label: string;
  position: { x: number; y: number };
  combatant_id?: string | null;
  controller_type: string;
  movement_speed_cells?: number | null;
  movement_budget?: number | null;
};

export type CombatMapPreviewObstacle = {
  cells: Array<{ x: number; y: number }>;
  blocks_movement: boolean;
  blocks_targeting: boolean;
  blocks_spell: boolean;
  cover?: string | null;
};

export type CombatActiveAreaEffect = {
  id: string;
  source_spell_canonical_key?: string | null;
  source_spell_name: string;
  caster_participant_id: string;
  caster_ref_id?: string | null;
  caster_character_id?: string | null;
  origin_point: { x: number; y: number };
  anchor_cell: { x: number; y: number };
  area_shape: "sphere" | "cone" | "line" | "cube" | "cylinder";
  size_meters: number;
  radius_meters?: number | null;
  length_meters?: number | null;
  side_meters?: number | null;
  affected_cells: Array<{ x: number; y: number }>;
  effect_kind: "obscurement" | "hazard" | "spell_area" | string;
  duration?: string | null;
  concentration_owner_participant_id?: string | null;
  concentration_owner_ref_id?: string | null;
  created_round?: number | null;
  created_turn_index?: number | null;
  obscurement?: string | null;
  terrain_effect?: string | null;
  movement_damage_dice?: string | null;
  damage_type?: string | null;
  damage_per_meters?: number | null;
};

export type CombatSpellAnchorMovement = {
  max_meters_per_follow_up?: number | null;
};

export type CombatSpellAnchor = {
  id: string;
  source_spell_key: string;
  source_spell_name?: string | null;
  owner_participant_id: string;
  created_by_participant_id: string;
  position: { x: number; y: number };
  duration_type: "rounds";
  remaining_rounds?: number | null;
  expires_on?: "turn_start" | "turn_end" | null;
  expires_at_participant_id?: string | null;
  render_kind: string;
  movement?: CombatSpellAnchorMovement | null;
  metadata?: Record<string, unknown>;
};

export type SpiritualWeaponActionRequest = {
  actor_participant_id: string;
  anchor_id: string;
  destination?: { x: number; y: number } | null;
  target_ref_id?: string | null;
  target_kind?: string | null;
};

export type CombatMapPreviewState = {
  session_id: string;
  version: number;
  grid_width: number;
  grid_height: number;
  tokens: CombatMapPreviewToken[];
  obstacles: CombatMapPreviewObstacle[];
  active_area_effects?: CombatActiveAreaEffect[];
  spell_anchors?: CombatSpellAnchor[];
};

export type CombatMapEnsureResponse = {
  session_id: string;
  combat_phase: CombatPhase;
  map_available: boolean;
  reason?: string | null;
};

export type PreviewPosition = { x: number; y: number };

export type CombatPreviewRequest = {
  source_ref_id: string;
  action_type: "move" | "attack" | "spell";
  target_ref_id?: string | null;
  source_position?: PreviewPosition | null;
  target_position?: PreviewPosition | null;
  reach_cells?: number;
  aoe_shape?: "sphere" | "cone" | "line" | "cube" | "cylinder" | null;
  aoe_size_cells?: number | null;
};

export type TacticalDiagnosticsPayload = {
  isValid: boolean;
  failureReasons: string[];
  checks: Record<string, boolean>;
  metadata: Record<string, unknown>;
};

export type CombatPreviewResponse = {
  diagnostics?: TacticalDiagnosticsPayload | null;
  effectiveReachCells: number;
  aoeCells: PreviewPosition[];
};

export type CombatAreaPreviewRequest = {
  actor_participant_id?: string | null;
  target_ref_id?: string | null;
  origin_cell: { x: number; y: number };
  anchor_cell: { x: number; y: number };
  inventory_item_id?: string | null;
  spell_id?: string | null;
  spell_canonical_key?: string | null;
  spell_mode?: CombatSpellMode | null;
  slot_level?: number | null;
};

export type AreaPreviewAffectedTargetSpatialMetadata = {
  target_ref_id: string;
  target_display_name?: string | null;
  /** Canonical values: "none" | "half" | "threeQuarters" | "full" | null */
  cover?: string | null;
  base_save_dc?: number | null;
  effective_save_dc?: number | null;
  cover_modifier?: number;
};

export type CombatAreaGuardrailOutcome = {
  target_ref_id: string;
  target_display_name: string;
  target_kind: CombatParticipantKind;
  excluded_by_guardrail?: boolean;
  guardrail_reason: string;
};

export type CombatAreaPreviewResponse = {
  is_valid: boolean;
  reason?: string | null;
  shape?: "sphere" | "cone" | "line" | "cube" | "cylinder" | null;
  affected_cells: Array<{ x: number; y: number }>;
  affected_target_ref_ids: string[];
  affected_token_ids: string[];
  map_version?: number | null;
  affected_target_spatial_metadata?: AreaPreviewAffectedTargetSpatialMetadata[];
  guardrail_target_outcomes?: CombatAreaGuardrailOutcome[];
};

export type CombatMovementPreviewRequest = {
  actor_participant_id?: string | null;
  destination_cell: { x: number; y: number };
};

export type CombatMovementPreviewResponse = {
  is_valid: boolean;
  reason?: string | null;
  source_cell?: { x: number; y: number } | null;
  destination_cell: { x: number; y: number };
  path: Array<{ x: number; y: number }>;
  path_cost_units: number;
  movement_budget: number;
  movement_speed_cells: number;
  remaining_budget: number;
  map_version?: number | null;
};

export type CombatEntityActionRequest = {
  actor_participant_id?: string | null;
  target_ref_id?: string | null;
  combat_action_id: string;
  has_advantage?: boolean;
  has_disadvantage?: boolean;
  roll_source?: RollSource;
  manual_roll?: number | null;
  manual_rolls?: [number, number] | null;
  concentration_roll_source?: RollSource;
  concentration_manual_roll?: number | null;
  override_resource_limit?: boolean;
};

export type CombatEntityActionResult = {
  action_name: string;
  action_kind:
    | "weapon_attack"
    | "spell_attack"
    | "saving_throw"
    | "heal"
    | "utility";
  damage: number;
  damage_type?: string | null;
  healing: number;
  is_critical?: boolean | null;
  is_hit?: boolean | null;
  is_saved?: boolean | null;
  new_hp?: number | null;
  roll?: number | null;
  save_dc?: number | null;
  save_roll?: number | null;
  save_success_outcome?: "none" | "half_damage" | null;
  roll_result?: RollResult | null;
  target_ac?: number | null;
  target_display_name?: string | null;
  damage_dice?: string | null;
  damage_bonus?: number | null;
  attack_bonus?: number | null;
  pending_attack_id?: string | null;
  pending_save_id?: string | null;
  damage_roll_required?: boolean;
  damage_rolls?: number[];
  base_damage?: number | null;
  damage_roll_source?: RollSource | null;
  concentration_check?: CombatConcentrationCheckResult | null;
};

export type CombatConcentrationCheckResult = {
  actor_participant_id?: string | null;
  actor_display_name: string;
  damage_taken: number;
  dc: number;
  success: boolean;
  roll_result: RollResult;
  broken_effect_labels?: string[];
  source_spell_keys?: string[];
  summary_text: string;
};

export type CombatResolveDamageRequest = {
  actor_participant_id?: string | null;
  pending_attack_id: string;
  roll_source?: RollSource;
  manual_rolls?: number[] | null;
  concentration_roll_source?: RollSource;
  concentration_manual_roll?: number | null;
};

export type CombatResolveSpellEffectRequest = {
  actor_participant_id?: string | null;
  pending_spell_id: string;
  roll_source?: RollSource;
  manual_rolls?: number[] | null;
  concentration_roll_source?: RollSource;
  concentration_manual_roll?: number | null;
};

export type CombatApplyDamageRequest = {
  target_ref_id: string;
  amount: number;
  kind: CombatParticipantKind;
  type_override?: string | null;
  concentration_roll_source?: RollSource;
  concentration_manual_roll?: number | null;
};

export type CombatApplyHealingRequest = {
  target_ref_id: string;
  amount: number;
  kind: CombatParticipantKind;
};

export type CombatDeathSaveRequest = {
  actor_participant_id?: string | null;
};

export type CombatApplyEffectRequest = {
  target_participant_id: string;
  kind: ActiveEffectKind;
  condition_type?: ActiveEffectConditionType | null;
  numeric_value?: number | null;
  duration_type?: ActiveEffectDurationType;
  remaining_rounds?: number | null;
  expires_at_participant_id?: string | null;
  source_participant_id?: string | null;
  metadata?: Record<string, unknown> | null;
  display_label?: string | null;
};

export type CombatRemoveEffectRequest = {
  target_participant_id: string;
  effect_id: string;
};

export type CombatConsumeReactionRequest = {
  participant_id: string;
  override_resource_limit?: boolean;
};

export type CombatReactionRequestRequest = {
  actor_participant_id: string;
};

export type CombatReactionResolveRequest = {
  actor_participant_id: string;
  decision: "approve" | "deny";
  override_resource_limit?: boolean;
};

export type StandardActionType =
  | "dodge"
  | "help"
  | "hide"
  | "use_object"
  | "dash"
  | "disengage"
  | "dragonborn_breath_weapon";

export type CombatStandardActionRequest = {
  action: StandardActionType;
  actor_participant_id?: string | null;
  target_participant_id?: string | null;
  inventory_item_id?: string | null;
  description?: string | null;
  roll_source?: RollSource;
  manual_roll?: number | null;
  manual_rolls?: number[] | null;
  override_resource_limit?: boolean;
};

export type CombatStandardActionResult = {
  action: StandardActionType;
  actor_name: string;
  message: string;
  roll_result?: RollResult | null;
  effect_applied: boolean;
  target_display_name?: string | null;
  target_kind?: CombatParticipantKind | null;
  healing?: number | null;
  damage?: number | null;
  damage_type?: string | null;
  new_hp?: number | null;
  save_ability?: string | null;
  save_dc?: number | null;
  is_saved?: boolean | null;
  save_success_outcome?: "none" | "half_damage" | null;
  effect_dice?: string | null;
  effect_rolls?: number[];
  effect_roll_source?: RollSource | null;
  uses_remaining?: number | null;
  concentration_check?: CombatConcentrationCheckResult | null;
};

export const combatRepo = {
  getState: (sessionId: string) =>
    http.get<CombatState>(`/sessions/${sessionId}/combat`),
  startCombat: (sessionId: string, payload: CombatStartRequest) =>
    http.post<CombatState>(`/sessions/${sessionId}/combat/start`, payload),
  setInitiative: (sessionId: string, payload: CombatSetInitiativeRequest) =>
    http.put<CombatState>(`/sessions/${sessionId}/combat/initiative`, payload),
  confirmPlacement: (sessionId: string) =>
    http.post<CombatState>(
      `/sessions/${sessionId}/combat/placement/confirm`,
      {}
    ),
  nextTurn: (sessionId: string, payload: CombatNextTurnRequest = {}) =>
    http.post<CombatState>(`/sessions/${sessionId}/combat/turn/next`, payload),
  endCombat: (sessionId: string) =>
    http.post<CombatState>(`/sessions/${sessionId}/combat/end`, {}),
  attack: (sessionId: string, payload: CombatAttackRequest) =>
    http.post<CombatAttackResult>(
      `/sessions/${sessionId}/combat/action/attack`,
      payload
    ),
  attackDamage: (sessionId: string, payload: CombatResolveDamageRequest) =>
    http.post<CombatAttackResult>(
      `/sessions/${sessionId}/combat/action/attack/damage`,
      payload
    ),
  castSpell: (sessionId: string, payload: CombatCastSpellRequest) =>
    http.post<CombatSpellResult>(
      `/sessions/${sessionId}/combat/action/cast`,
      payload
    ),
  resolveSpellContext: (sessionId: string, payload: CombatResolveSpellContextRequest) =>
    http.post<CombatResolvedSpellContext>(
      `/sessions/${sessionId}/combat/spells/resolve-context`,
      payload,
    ),
  ensureMap: (sessionId: string) =>
    http.post<CombatMapEnsureResponse>(
      `/sessions/${sessionId}/combat/map/ensure`,
      {}
    ),
  getMapState: (sessionId: string, actorParticipantId?: string | null) =>
    http.get<CombatMapPreviewState>(
      `/sessions/${sessionId}/combat/map-state${actorParticipantId ? `?actor_participant_id=${encodeURIComponent(actorParticipantId)}` : ""}`
    ),
  previewAreaSpell: (sessionId: string, payload: CombatAreaPreviewRequest) =>
    http.post<CombatAreaPreviewResponse>(
      `/sessions/${sessionId}/combat/action/cast/preview`,
      payload
    ),
  previewMovement: (sessionId: string, payload: CombatMovementPreviewRequest) =>
    http.post<CombatMovementPreviewResponse>(
      `/sessions/${sessionId}/combat/action/move/preview`,
      payload
    ),
  confirmMovement: (sessionId: string, payload: CombatMovementPreviewRequest) =>
    http.post<CombatMovementPreviewResponse>(
      `/sessions/${sessionId}/combat/action/move`,
      payload
    ),
  previewAction: (sessionId: string, payload: CombatPreviewRequest) =>
    http.post<CombatPreviewResponse>(
      `/sessions/${sessionId}/combat/preview`,
      payload
    ),
  castSpellEffect: (
    sessionId: string,
    payload: CombatResolveSpellEffectRequest
  ) =>
    http.post<CombatSpellResult>(
      `/sessions/${sessionId}/combat/action/cast/effect`,
      payload
    ),
  entityAction: (sessionId: string, payload: CombatEntityActionRequest) =>
    http.post<CombatEntityActionResult>(
      `/sessions/${sessionId}/combat/action/entity`,
      payload
    ),
  entityActionDamage: (
    sessionId: string,
    payload: CombatResolveDamageRequest
  ) =>
    http.post<CombatEntityActionResult>(
      `/sessions/${sessionId}/combat/action/entity/damage`,
      payload
    ),
  applyDamage: (sessionId: string, payload: CombatApplyDamageRequest) =>
    http.post<any>(
      `/sessions/${sessionId}/combat/action/apply-damage`,
      payload
    ),
  deathSave: (sessionId: string, payload: CombatDeathSaveRequest = {}) =>
    http.post<any>(`/sessions/${sessionId}/combat/action/death-save`, payload),
  revive: (sessionId: string, payload: CombatReviveRequest) =>
    http.post<CombatReviveResult>(
      `/sessions/${sessionId}/combat/action/revive`,
      payload
    ),
  applyEffect: (sessionId: string, payload: CombatApplyEffectRequest) =>
    http.post<CombatState>(
      `/sessions/${sessionId}/combat/effects/apply`,
      payload
    ),
  removeEffect: (sessionId: string, payload: CombatRemoveEffectRequest) =>
    http.post<CombatState>(
      `/sessions/${sessionId}/combat/effects/remove`,
      payload
    ),
  standardAction: (sessionId: string, payload: CombatStandardActionRequest) =>
    http.post<CombatStandardActionResult>(
      `/sessions/${sessionId}/combat/action/standard`,
      payload
    ),
  spiritualWeaponAction: (sessionId: string, payload: SpiritualWeaponActionRequest) =>
    http.post<Record<string, unknown>>(
      `/sessions/${sessionId}/combat/spiritual-weapon-action`,
      payload
    ),
  consumeReaction: (sessionId: string, payload: CombatConsumeReactionRequest) =>
    http.post<CombatState>(
      `/sessions/${sessionId}/combat/action/consume-reaction`,
      payload
    ),
  requestReaction: (sessionId: string, payload: CombatReactionRequestRequest) =>
    http.post<CombatState>(
      `/sessions/${sessionId}/combat/action/reaction/request`,
      payload
    ),
  resolveReaction: (sessionId: string, payload: CombatReactionResolveRequest) =>
    http.post<CombatState>(
      `/sessions/${sessionId}/combat/action/reaction/resolve`,
      payload
    ),
  resolvePendingSave: (
    sessionId: string,
    payload: {
      target_participant_id: string;
      pending_save_id: string;
      roll_source?: RollSource;
      manual_roll?: number | null;
      manual_rolls?: number[] | null;
    },
  ) =>
    http.post<CombatSpellResult>(
      `/sessions/${sessionId}/combat/action/save-resolve`,
      payload,
    ),
  listEffects: (sessionId: string) =>
    http.get<ActiveEffect[]>(`/sessions/${sessionId}/combat/effects`),
  updateDistances: (sessionId: string, payload: CombatUpdateDistancesRequest) =>
    http.patch<CombatState>(`/sessions/${sessionId}/combat/distances`, payload)
};
