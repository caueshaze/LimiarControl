# Combat Spells Phase 3A

## Scope

Phase 3A supports only single-target spell resolution for:

- `spell_attack`
- `saving_throw`
- `direct_damage`
- `heal`

It does **not** support AoE, concentration, durations, conditions, riders, or multi-target resolution.

## `pending_spell_effect` lifecycle

Player spell effects use the participant-level `pending_attack` slot in `CombatState`, but they are always marked with `type="player_spell_effect"`.

Lifecycle:

1. `cast_spell` resolves the gate first:
   - `spell_attack`: authoritative attack roll vs target AC
   - `saving_throw`: authoritative target save vs save DC
   - `direct_damage` / `heal`: no hit/save gate
2. If the spell still needs damage/healing dice, the backend creates a pending entry with:
   - `id`
   - `type="player_spell_effect"`
   - target metadata
   - spell metadata
   - saved roll result from the hit/save step when applicable
3. The client resolves the second step through `POST /combat/action/cast/effect`.
4. The backend applies HP/status changes, emits realtime/log events, and clears the pending entry.
5. Any new spell cast by the same actor clears stale pending spell state before starting a new flow.

This keeps the state shape stable while making the spell-effect lifecycle explicit.

## `direct_damage` policy

`direct_damage` is an explicit fallback flow for spells that are already known to be single-target direct damage in this phase.

Rules:

- it must be selected explicitly
- it is **not** the default fallback for spells with structured saving throw semantics
- if the catalog says the spell uses a saving throw, the backend rejects `direct_damage`
- textual descriptions are not used as a source of truth

This is intentionally conservative so `direct_damage` does not become a bypass around `spell_attack` or `saving_throw`.

## Saving throw limitation

Current `saving_throw` handling is binary in Phase 3A:

- failed save: apply the spell effect
- successful save: negate the effect for this phase

Supported today:

- full damage on failed save
- full heal where applicable

Not supported yet:

- half damage on successful save
- partial scaling by save result
- rider effects on success/failure

## Validation status

Phase 3A should only be considered fully closed after validation in the real backend environment with:

- `sqlalchemy`
- `sqlmodel`
- ORM/database wiring
- realtime wiring

Local lightweight validation may pass while ORM/runtime integration still has issues, so real-backend smoke tests remain required.
