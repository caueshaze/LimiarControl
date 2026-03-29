# Spell Semantics — Taxonomy Reference

This document describes the authoritative classification taxonomy for spells in LimiarControl, covering `resolutionType`, `upcastMode`, and their interaction with related fields.

---

## Resolution Type (`resolutionType`)

Resolution type describes **the primary systemic effect** a spell produces on its targets or the world — not the mechanical resolution method (attack roll vs. saving throw). Resolution method is captured separately via `savingThrow`.

| Value | Description | Example Spells |
|-------|-------------|----------------|
| `damage` | The spell deals damage to one or more targets | Fireball, Eldritch Blast, Fire Bolt |
| `heal` | The spell restores hit points | Cure Wounds, Healing Word, Goodberry (partial) |
| `buff` | The spell enhances the caster or allies (offensive capability, defense, mobility) | Shield, Hunter's Mark, Bless, Haste |
| `debuff` | The spell impairs a target's capabilities without full control (penalty to rolls, reduced speed, etc.) | Bane, Hex (mechanical penalty focus) |
| `control` | The spell restricts or eliminates a target's agency (paralysis, sleep, charm, fear) | Hold Person, Sleep, Animal Friendship |
| `utility` | The spell produces a non-combat effect (information, movement, communication, environment) | Detect Magic, Goodberry (food provision), Misty Step |

### Classification Criteria

**`buff` vs `debuff`**: The primary question is: who carries the mechanical benefit?
- If the spell's main effect **enhances the caster or an ally** (even if it requires marking/targeting an enemy), classify as `buff`. Hunter's Mark marks a target, but the mechanical payload is +1d6 to the *caster's* weapon attacks — this is an **offensive caster buff**.
- If the spell's main effect **reduces an enemy's capabilities** (penalty to their rolls, reduced stats), classify as `debuff`.

**`control` vs `debuff`**: Control removes or severely restricts the target's action options (cannot move, cannot take actions, etc.). Debuff reduces effectiveness without removing agency.

**`utility` vs others**: If a spell has dual purposes (e.g., Goodberry provides food *and* healing), classify by the **primary systemic utility in the context of this game**. Goodberry is classified as `utility` because its healing use is an incidental property of the food item it creates; the spell doesn't directly heal.

### Field Constraints by Resolution Type

| Resolution Type | `savingThrow` | `damageDice`/`damageType` | `healDice` | `saveSuccessOutcome` |
|----------------|---------------|--------------------------|------------|----------------------|
| `damage` | allowed | allowed | not stored | allowed if savingThrow set |
| `heal` | not stored | not stored | **required** | not stored |
| `buff` | not stored | not stored | not stored | not stored |
| `debuff` | allowed | not stored | not stored | not stored |
| `control` | allowed | not stored | not stored | not stored |
| `utility` | not stored | not stored | not stored | not stored |

All constraints are enforced by `cross_field_validation` in `BaseSpellWrite`. Violations are silently cleared (not rejected as errors) so that changing resolution type in the admin UI doesn't require manually clearing every field.

### Known Limitation: `saveSuccessOutcome`

`saveSuccessOutcome` is currently restricted to **`damage` + `savingThrow` combinations only**. Control and debuff spells that have saving throws where success produces a partial outcome (e.g., "success: not charmed, but shaken for 1 round") cannot express this in the current schema. This is an intentional scope limitation — the field exists for the most common case (save for half damage). Partial outcomes for non-damage spells would require a more expressive outcome model.

---

## Upcast Mode (`upcastMode`)

Upcast mode describes **how the spell's effect changes** when cast at a higher slot level.

| Value | Description | Required Fields | Example Spells |
|-------|-------------|-----------------|----------------|
| `extra_damage_dice` | Additional damage dice per slot level | `dice` and/or `flat` | Fireball, Burning Hands |
| `extra_heal_dice` | Additional healing dice per slot level | `dice` and/or `flat` | Cure Wounds, Healing Word |
| `flat_bonus` | A flat numeric bonus per slot level | `flat` | Some homebrew spells |
| `additional_targets` | Affects one more target per slot level | `perLevel` | Hold Person, Animal Friendship |
| `duration_scaling` | Duration increases per slot level | `perLevel` | Hunter's Mark |
| `effect_scaling` | A non-dice effect scales up (AC bonus, range, etc.) | `scalingKey`, `scalingSummary` (required); `scalingEditorial` (optional) | Shield (conceptual), Arcane Eye |
| `extra_effect` | A qualitatively new effect is unlocked | `unlockKey`, `unlockSummary` (required); `unlockEditorial` (optional) | Prismatic Spray, Simulacrum |

### Structured Payloads

#### `effect_scaling`

Use this when the upcast improvement is non-quantitative (not more dice, not more targets), but rather a *change to how the existing effect works*.

```json
{
  "mode": "effect_scaling",
  "scalingKey": "armor_class_bonus",
  "scalingSummary": "+1 to the AC bonus per slot level above 1st",
  "scalingEditorial": "Optional: note about edge cases",
  "perLevel": 1
}
```

- `scalingKey`: Machine-readable identifier for what is scaling (snake_case)
- `scalingSummary`: Human-readable description shown to GMs/players
- `scalingEditorial`: Optional clarification, ruling, or edge case note

#### `extra_effect`

Use this when upcasting unlocks a qualitatively new capability that didn't exist at the base level.

```json
{
  "mode": "extra_effect",
  "unlockKey": "additional_beam",
  "unlockSummary": "Create one additional Eldritch Blast beam per slot level above 1st",
  "unlockEditorial": "Optional: note about interactions with Agonizing Blast",
  "perLevel": 1
}
```

- `unlockKey`: Machine-readable identifier for the unlocked capability (snake_case)
- `unlockSummary`: Human-readable description of what becomes available
- `unlockEditorial`: Optional clarification or interaction note

---

## Combat Mode Derivation

The frontend derives a suggested `CombatSpellMode` from `resolutionType` and `savingThrow`:

| `resolutionType` | `savingThrow` | Suggested combat mode |
|-----------------|---------------|----------------------|
| `heal` | — | `heal` |
| `damage` | set | `saving_throw` |
| `damage` | not set | `spell_attack` |
| `control` or `debuff` | set | `saving_throw` |
| any other | — | `utility` |

Spells can override this via `SPELL_AUTOMATION_REGISTRY` in `spellAutomation.ts` by setting an explicit `defaultMode`.

---

## Notable Spell Classifications

| Spell | Resolution Type | Notes |
|-------|----------------|-------|
| Hunter's Mark | `buff` | Marks a target to enhance *caster's* attacks — offensive caster buff |
| Shield | `buff` | Reactive (+5 AC, immunity to Magic Missile) — defensive caster buff |
| Goodberry | `utility` | Creates food; healing is a property of the item, not the spell effect |
| Animal Friendship | `control` | Charmed condition on a WIS save — restricts target's agency |
| Hold Person | `control` | Paralyzed condition on a WIS save — removes target's agency |
| Bless | `buff` | Adds d4 to attack rolls and saving throws of allies |
| Hex | `debuff` | Disadvantage on chosen ability checks — reduces target capability |
