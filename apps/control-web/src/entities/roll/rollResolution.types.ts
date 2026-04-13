// Canonical IDs — must match backend (campaign_entity_shared.py).
// Abilities: lowercase. Skills: camelCase (PHB convention used in backend).
// Frontend uses these strings directly in payloads, no intermediate mapping.

export type AdvantageMode = "normal" | "advantage" | "disadvantage";
export type ActorKind = "player" | "session_entity";
export type RollType = "ability" | "save" | "skill" | "initiative" | "attack";
export type RollSource = "system" | "manual";

export type AbilityName =
  | "strength"
  | "dexterity"
  | "constitution"
  | "intelligence"
  | "wisdom"
  | "charisma";

export type SkillName =
  | "acrobatics"
  | "animalHandling"
  | "arcana"
  | "athletics"
  | "deception"
  | "history"
  | "insight"
  | "intimidation"
  | "investigation"
  | "medicine"
  | "nature"
  | "perception"
  | "performance"
  | "persuasion"
  | "religion"
  | "sleightOfHand"
  | "stealth"
  | "survival";

// --- Requests (sent to backend) ---

export type AbilityRollRequest = {
  actor_kind: ActorKind;
  actor_ref_id: string;
  ability: AbilityName;
  advantage_mode: AdvantageMode;
  bonus_override?: number | null;
  dc?: number | null;
  roll_source?: RollSource;
  manual_roll?: number | null;
  manual_rolls?: [number, number] | null;
};

export type SaveRollRequest = {
  actor_kind: ActorKind;
  actor_ref_id: string;
  ability: AbilityName;
  advantage_mode: AdvantageMode;
  bonus_override?: number | null;
  dc?: number | null;
  roll_source?: RollSource;
  manual_roll?: number | null;
  manual_rolls?: [number, number] | null;
};

export type SkillRollRequest = {
  actor_kind: ActorKind;
  actor_ref_id: string;
  skill: SkillName;
  advantage_mode: AdvantageMode;
  bonus_override?: number | null;
  dc?: number | null;
  roll_source?: RollSource;
  manual_roll?: number | null;
  manual_rolls?: [number, number] | null;
};

export type InitiativeRollRequest = {
  actor_kind: ActorKind;
  actor_ref_id: string;
  advantage_mode: AdvantageMode;
  bonus_override?: number | null;
  roll_source?: RollSource;
  manual_roll?: number | null;
  manual_rolls?: [number, number] | null;
};

export type AttackBaseRollRequest = {
  actor_kind: ActorKind;
  actor_ref_id: string;
  advantage_mode: AdvantageMode;
  bonus_override?: number | null;
  target_ac?: number | null;
  roll_source?: RollSource;
  manual_roll?: number | null;
  manual_rolls?: [number, number] | null;
};

// --- Result (received from backend + via realtime) ---

export type RollResult = {
  event_id: string;
  roll_type: RollType;
  actor_kind: ActorKind;
  actor_ref_id: string;
  actor_display_name: string;
  rolls: number[];
  selected_roll: number;
  advantage_mode: AdvantageMode;
  modifier_used: number;
  override_used: boolean;
  formula: string;
  total: number;
  ability?: string | null;
  skill?: string | null;
  dc?: number | null;
  target_ac?: number | null;
  success?: boolean | null;
  is_gm_roll: boolean;
  roll_source: RollSource;
  timestamp: string;
};
