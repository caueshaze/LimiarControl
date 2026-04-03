import type { RollResult, RollSource } from "../../entities/roll/rollResolution.types";
import { http } from "./http";

export type CombatPhase = "initiative" | "active" | "ended";
export type CombatParticipantKind = "player" | "session_entity";
export type CombatSpellMode = "spell_attack" | "saving_throw" | "direct_damage" | "heal" | "utility";
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
  | "charmed";

export type ActiveEffectDurationType =
  | "manual"
  | "rounds"
  | "until_turn_start"
  | "until_turn_end";

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
  created_at: string;
  metadata?: Record<string, unknown> | null;
  display_label?: string | null;
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
};

export type CombatState = {
  id: string;
  session_id: string;
  phase: CombatPhase;
  round: number;
  current_turn_index: number;
  participants: CombatParticipant[];
  created_at: string;
  updated_at?: string | null;
};

export type CombatStartRequest = {
  participants: CombatParticipant[];
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
  target_ref_id: string;
  inventory_item_id?: string | null;
  spell_id?: string | null;
  spell_canonical_key?: string | null;
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

export type CombatSpellResult = {
  spell_name: string;
  spell_canonical_key?: string | null;
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
  target_display_name: string;
  target_kind: CombatParticipantKind;
  save_ability?: string | null;
  save_dc?: number | null;
  save_success_outcome?: "none" | "half_damage" | null;
  effect_dice?: string | null;
  effect_bonus?: number | null;
  pending_spell_id?: string | null;
  effect_roll_required?: boolean;
  effect_rolls?: number[];
  base_effect?: number | null;
  effect_roll_source?: RollSource | null;
  action_cost?: CombatActionCost | null;
  summary_text?: string | null;
  inventory_refresh_required?: boolean;
  concentration_check?: CombatConcentrationCheckResult | null;
  elemental_affinity_eligible?: boolean;
  elemental_affinity_damage_type?: string | null;
  elemental_affinity_bonus?: number | null;
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
  action_kind: "weapon_attack" | "spell_attack" | "saving_throw" | "heal" | "utility";
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
  nextTurn: (sessionId: string, payload: CombatNextTurnRequest = {}) =>
    http.post<CombatState>(`/sessions/${sessionId}/combat/turn/next`, payload),
  endCombat: (sessionId: string) =>
    http.post<CombatState>(`/sessions/${sessionId}/combat/end`, {}),
  attack: (sessionId: string, payload: CombatAttackRequest) =>
    http.post<CombatAttackResult>(`/sessions/${sessionId}/combat/action/attack`, payload),
  attackDamage: (sessionId: string, payload: CombatResolveDamageRequest) =>
    http.post<CombatAttackResult>(`/sessions/${sessionId}/combat/action/attack/damage`, payload),
  castSpell: (sessionId: string, payload: CombatCastSpellRequest) =>
    http.post<CombatSpellResult>(`/sessions/${sessionId}/combat/action/cast`, payload),
  castSpellEffect: (sessionId: string, payload: CombatResolveSpellEffectRequest) =>
    http.post<CombatSpellResult>(`/sessions/${sessionId}/combat/action/cast/effect`, payload),
  entityAction: (sessionId: string, payload: CombatEntityActionRequest) =>
    http.post<CombatEntityActionResult>(`/sessions/${sessionId}/combat/action/entity`, payload),
  entityActionDamage: (sessionId: string, payload: CombatResolveDamageRequest) =>
    http.post<CombatEntityActionResult>(`/sessions/${sessionId}/combat/action/entity/damage`, payload),
  applyDamage: (sessionId: string, payload: CombatApplyDamageRequest) =>
    http.post<any>(`/sessions/${sessionId}/combat/action/apply-damage`, payload),
  deathSave: (sessionId: string, payload: CombatDeathSaveRequest = {}) =>
    http.post<any>(`/sessions/${sessionId}/combat/action/death-save`, payload),
  revive: (sessionId: string, payload: CombatReviveRequest) =>
    http.post<CombatReviveResult>(`/sessions/${sessionId}/combat/action/revive`, payload),
  applyEffect: (sessionId: string, payload: CombatApplyEffectRequest) =>
    http.post<CombatState>(`/sessions/${sessionId}/combat/effects/apply`, payload),
  removeEffect: (sessionId: string, payload: CombatRemoveEffectRequest) =>
    http.post<CombatState>(`/sessions/${sessionId}/combat/effects/remove`, payload),
  standardAction: (sessionId: string, payload: CombatStandardActionRequest) =>
    http.post<CombatStandardActionResult>(`/sessions/${sessionId}/combat/action/standard`, payload),
  consumeReaction: (sessionId: string, payload: CombatConsumeReactionRequest) =>
    http.post<CombatState>(`/sessions/${sessionId}/combat/action/consume-reaction`, payload),
  requestReaction: (sessionId: string, payload: CombatReactionRequestRequest) =>
    http.post<CombatState>(`/sessions/${sessionId}/combat/action/reaction/request`, payload),
  resolveReaction: (sessionId: string, payload: CombatReactionResolveRequest) =>
    http.post<CombatState>(`/sessions/${sessionId}/combat/action/reaction/resolve`, payload),
  listEffects: (sessionId: string) =>
    http.get<ActiveEffect[]>(`/sessions/${sessionId}/combat/effects`),
};
