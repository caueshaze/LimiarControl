# Feature Specification: Tactical Battle Map System

**Feature Branch**: `001-tactical-battle-map`  
**Created**: 2026-03-31  
**Status**: Draft  
**Input**: User description: "Tactical Battle Map system for Limiar.

A real-time grid-based combat map where players control tokens representing
their characters. The system supports movement, turn-based combat, and spell
targeting with area calculations.

Core features:
- Grid-based movement (cell to cell)
- Token ownership (player vs GM)
- Server-authoritative validation of actions
- Real-time synchronization across clients
- Obstacle and collision handling
- Turn-based combat support
- Spell targeting system with area preview (line, cone, sphere, cube)

The system must ensure deterministic behavior, consistent state across all
clients, and strict separation between client visualization and server
authority."

## Clarifications

### Session 2026-03-31

- Q: Which grid movement model should the system use? → A: Diagonals with alternating cost
- Q: How should obstacles affect spell targeting? → A: Obstacles block movement and also block spell lines/areas where applicable
- Q: Who controls combat state progression? → A: LimiarControl controls combat turn progression, while LimiarMap validates and applies tactical movement according to the authoritative combat state
- Q: Does spell handling include effect resolution in this feature? → A: Targeting only, no effect resolution

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Move Tokens in Live Combat (Priority: P1)

As a player or GM, I want to move a controlled token across the battle grid and
see the validated result reflected for all connected participants so that combat
positioning remains reliable and shared.

**Why this priority**: Movement and synchronized positioning are the minimum
viable capability for a tactical battle map and the foundation for all later
combat and targeting rules.

**Independent Test**: Start a combat map with at least two connected clients,
move an authorized token across valid cells, and verify the server accepts legal
movement, rejects illegal movement, and all clients converge on the same final
token position.

**Acceptance Scenarios**:

1. **Given** a player controls a token and the destination cells are open,
   **When** the player submits a move within the allowed path, **Then** the
   system updates the token position to the validated destination on all
   clients.
2. **Given** a token attempts to move through a blocked or occupied cell,
   **When** the move is submitted, **Then** the system rejects the move and all
   clients retain the prior authoritative position.
3. **Given** a user tries to move a token they do not control, **When** the
   action is submitted, **Then** the system rejects the action and shows no
   authoritative state change to other clients.

---

### User Story 2 - Run Turn-Based Combat (Priority: P2)

As a GM, I want the shared map to reflect authoritative turn order and round
progression from LimiarControl so that every participant can act in a consistent
combat sequence.

**Why this priority**: Turn structure is essential for coordinated multiplayer
combat once movement is reliable, and authoritative turn state directly affects
permissions and timing for all tactical actions on the map.

**Independent Test**: Begin a combat encounter, allow LimiarControl to advance
turns and map movement state, and verify every client sees the same active
combatant, round number, and action eligibility at each step.

**Acceptance Scenarios**:

1. **Given** combat is active with an ordered list of combatants, **When**
   LimiarControl advances the turn, **Then** all clients display the same next
   active combatant and updated round state.
2. **Given** it is not a token's turn, **When** its controller attempts a
   turn-restricted action, **Then** the system rejects the action and preserves
   the current combat state.

---

### User Story 3 - Preview and Resolve Spell Targeting (Priority: P3)

As a player or GM, I want to preview legal spell targeting areas on the grid and
submit a spell target for validation so that area-based abilities resolve
consistently and transparently.

**Why this priority**: Spell targeting depends on stable movement, occupancy,
and turn state, so it belongs after the core map and combat flow are working.

**Independent Test**: Select each supported targeting shape, preview its area on
the grid, submit a legal and an illegal target, and verify the server-approved
area and affected cells are identical for all connected clients.

**Acceptance Scenarios**:

1. **Given** a spell uses a supported targeting shape and valid origin, **When**
   the user previews the target area, **Then** the system displays the expected
   affected cells without changing authoritative combat state.
2. **Given** a submitted spell target is legal for the acting token and current
   combat state, **When** the action is confirmed, **Then** the server validates
   the area and all clients receive the same resolved target footprint without
   applying downstream spell effects in this feature.
3. **Given** a submitted spell target violates range, shape, or obstruction
   rules, **When** the action is confirmed, **Then** the system rejects the
   action and leaves the authoritative state unchanged.

### Edge Cases

- If two clients submit conflicting actions for the same token, the server
  accepts only the first valid action for the current authoritative state and
  rejects later submissions that no longer apply.
- If a client predicts movement or targeting locally and the server rejects it,
  the client must revert to the authoritative server state without leaving a
  stale token position or targeting overlay.
- If a realtime update is delayed, duplicated, or replayed after reconnect, the
  receiving client must reapply it safely or ignore it without creating a second
  state change.
- If a token is surrounded by blocked or occupied cells, the system must make it
  clear that no legal movement destination exists.
- If an obstacle intersects a spell area, the system must calculate affected
  cells using the same grid rules on every client-visible result, and any
  obstacle that blocks spell propagation must exclude blocked cells beyond the
  obstruction where applicable.
- If a player disconnects during their turn, the current combat state must
  remain recoverable when they reconnect and resynchronize.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST present a discrete battle grid where each token
  occupies one defined cell at a time.
- **FR-002**: The system MUST allow the GM to place, remove, and reposition
  tokens on the grid.
- **FR-003**: The system MUST allow players to issue actions only for tokens
  they control, while the GM MUST be able to issue actions for any token.
- **FR-003a**: The system MUST treat LimiarControl as the authority for combat
  turn progression, while LimiarMap validates and applies tactical movement
  within the currently authoritative combat state.
- **FR-004**: The backend MUST be the sole authoritative source for token
  positions, combat state, validated targeting results, and derived tactical
  state relevant to this feature.
- **FR-005**: The system MUST validate every movement request against movement
  rules, including diagonal movement with alternating cost, cell occupancy,
  obstacle constraints, and token permissions before applying the result.
- **FR-006**: The system MUST synchronize authoritative state changes to all
  connected clients so that each client converges on the same map state after an
  accepted action.
- **FR-007**: The system MUST reject unauthorized, invalid, or out-of-turn
  actions without mutating authoritative state.
- **FR-008**: The system MUST support obstacle and collision handling that
  prevents tokens from entering blocked or occupied cells.
- **FR-008a**: The system MUST apply obstacle rules consistently to spell
  targeting so that obstacles block spell lines and areas where the shape or
  propagation rule depends on unobstructed grid paths.
- **FR-009**: The system MUST support turn-based combat with explicit tracking
  of active combatant, turn order, and round progression.
- **FR-009a**: The system MUST accept combat turn advancement only from
  LimiarControl or backend processes acting on its authority, and MUST enforce
  that tactical actions on the map conform to the current authoritative combat
  state.
- **FR-010**: The system MUST enforce turn-based restrictions for actions that
  require an active turn.
- **FR-011**: The system MUST support spell targeting previews for the following
  area shapes: line, cone, sphere, and cube.
- **FR-012**: The system MUST treat targeting previews as non-authoritative UI
  state until the player or GM confirms the action.
- **FR-013**: The system MUST validate submitted spell targets against the
  acting token's permissions, current combat state, supported shape rules, and
  grid-based area calculations, including obstacle blocking rules, before
  applying results.
- **FR-013a**: The system MUST stop spell processing at validated target area
  resolution for this feature and MUST NOT apply damage, conditions, or other
  downstream spell effects.
- **FR-014**: The system MUST resolve movement distance, targeting range, area
  footprints, obstacle interactions, and occupancy checks using deterministic
  grid-based rules, including the defined diagonal movement cost model.
- **FR-015**: The system MUST ensure duplicate or replayed realtime events do
  not create duplicate authoritative state changes.
- **FR-016**: The system MUST automatically resynchronize a client to the latest
  authoritative state after reconnect or after detecting local divergence.
- **FR-017**: The system MUST separate visualization state from authoritative
  state so that local previews, hover state, and transient highlights do not
  alter gameplay data unless confirmed and validated.
- **FR-018**: The system MUST record enough action outcome information for users
  to understand whether a submitted movement or targeting action was accepted or
  rejected.

### Key Entities *(include if feature involves data)*

- **Battle Map**: The shared tactical play space containing the grid layout,
  obstacles, tokens, and combat context for a single encounter.
- **Grid Cell**: A single discrete position on the battle map with occupancy and
  movement relevance.
- **Token**: A combat piece representing a player character, ally, enemy, or GM
  controlled unit, including ownership, current cell, and combat participation.
- **Controller**: The actor authorized to issue actions for a token, either a
  player for owned tokens or the GM for any token.
- **Combat State**: The turn-based encounter data including initiative order,
  active turn, round count, and action eligibility.
- **Obstacle**: A map element that blocks movement, targeting, or occupancy
  according to grid rules.
- **Targeting Shape**: A declared area definition used for preview and spell
  validation, including line, cone, sphere, and cube.
- **Realtime Action Event**: A structured action or state-change message used to
  apply, reject, replay safely, or resynchronize authoritative updates.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In moderated playtests, 95% of valid token moves are reflected to
  all connected participants within 1 second of submission.
- **SC-002**: In moderated playtests, 100% of rejected movement, targeting, and
  permission violations leave all clients showing the same final authoritative
  state.
- **SC-003**: In scenario-based testing, 100% of repeated executions of the same
  movement path or targeting input from the same starting state produce the same
  final occupied cells and affected area.
- **SC-004**: In usability validation, at least 90% of participants can
  complete a movement turn and confirm a legal spell target without facilitator
  intervention.
- **SC-005**: In reconnection testing, clients recover to the current
  authoritative combat state within 3 seconds of reconnecting in 95% of cases.

## Assumptions

- The initial release targets live multiplayer encounters rather than offline or
  play-by-post use.
- Each token occupies exactly one grid cell in the initial version.
- Movement supports diagonal travel using an alternating-cost model rather than
  equal-cost diagonal steps.
- Players control only their own designated tokens, while the GM retains
  unrestricted control over all tokens on the map.
- LimiarControl is the authoritative controller for combat turn progression in
  the initial release, while LimiarMap executes tactical movement subject to
  that authoritative combat state.
- The first release supports the listed targeting shapes only: line, cone,
  sphere, and cube.
- Obstacles that block movement also block spell propagation where the targeting
  rule depends on line or area traversal across the grid.
- Spell preview shows affected cells but does not resolve damage, saving throws,
  or broader character-sheet mechanics in this feature.
- Confirmed scope for this feature ends at validated targeting and affected-cell
  resolution rather than full spell effect execution.
- The initial release prioritizes desktop or tablet style play surfaces; mobile
  specific optimization is outside the first scope.
- The battle map uses a single shared encounter state per session rather than
  simultaneous independent combats on one map.
