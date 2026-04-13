# Data Model: Tactical Battle Map System

## BattleMap

**Purpose**: Represents the shared tactical encounter space and immutable map
configuration for a single live session.

**Fields**
- `id`: unique battle map identifier
- `name`: display name for the encounter
- `gridWidth`: number of grid columns
- `gridHeight`: number of grid rows
- `terrainVersion`: version marker for obstacle/layout changes
- `activeEncounterId`: linked encounter state identifier

**Relationships**
- Has many `GridCell`
- Has many `Obstacle`
- Has many `Token`
- Has one `CombatState`

## GridCell

**Purpose**: Defines a discrete playable location on the battle map.

**Fields**
- `x`: zero-based column index
- `y`: zero-based row index
- `isBlocked`: whether the cell blocks occupancy
- `occupantTokenId`: optional token occupying the cell

**Validation Rules**
- Coordinate pairs must be unique within a battle map
- A blocked cell cannot hold a token
- At most one token may occupy a cell

## Obstacle

**Purpose**: Defines map geometry that affects movement and targeting.

**Fields**
- `id`: unique obstacle identifier
- `battleMapId`: parent map identifier
- `cells`: list of occupied or blocked grid coordinates
- `blocksMovement`: whether tokens may traverse the obstacle
- `blocksTargeting`: whether spell propagation or line-based targeting stops at the obstacle

**Validation Rules**
- Every referenced cell must exist on the map
- `blocksTargeting` must be consistent with clarified obstacle rules for this feature

## Token

**Purpose**: Represents a combat unit under player, GM, or system control.

**Fields**
- `id`: unique token identifier
- `battleMapId`: parent map identifier
- `label`: player-facing token name
- `kind`: player character, ally, enemy, or neutral
- `controllerType`: `player`, `gm`, or `limiarControl`
- `controllerId`: actor identifier for authorization
- `position`: current grid coordinate
- `movementBudget`: allowed movement for the current turn
- `combatantId`: optional reference into initiative order

**Validation Rules**
- Tokens occupy exactly one non-blocked cell
- `controllerId` is required for player-controlled tokens
- Position must be unique among active tokens on the same map

## CombatState

**Purpose**: Tracks the authoritative turn-based flow of the encounter as
provided by LimiarControl and enforced by LimiarMap.

**Fields**
- `id`: unique combat state identifier
- `battleMapId`: parent map identifier
- `status`: `inactive`, `active`, or `completed`
- `roundNumber`: current round count
- `turnIndex`: index into initiative order
- `activeCombatantId`: combatant currently allowed to act
- `initiativeOrder`: ordered list of combatant identifiers
- `advancedBy`: authority marker for combat progression, expected to 
be `LimiarControl`
- `version`: monotonic encounter version for replay-safe sequencing

**Validation Rules**
- `activeCombatantId` must exist in `initiativeOrder` when status is `active`
- Round and turn values must advance monotonically under authoritative control

**State Transitions**
- `inactive -> active`: combat starts
- `active -> active`: turn advances, round increments when initiative wraps
- `active -> completed`: combat ends

## MovementAction

**Purpose**: Represents a requested token move before or after server validation.

**Fields**
- `actionId`: unique idempotency key
- `tokenId`: moving token
- `requestedPath`: ordered list of target cells
- `submittedBy`: actor identifier
- `submittedAtVersion`: encounter version seen by the requester
- `result`: `pending`, `accepted`, or `rejected`
- `rejectionReason`: optional failure explanation

**Validation Rules**
- Path must be contiguous on the grid
- Diagonal steps use alternating cost
- Path may not cross blocked or occupied cells
- Authorization must match token control and turn restrictions
- Movement must be legal under the current authoritative combat state

## TargetingTemplate

**Purpose**: Defines a previewable and validatable targeting request for a spell
or area action.

**Fields**
- `actionId`: unique idempotency key
- `tokenId`: acting token
- `shape`: `line`, `cone`, `sphere`, or `cube`
- `originCell`: source coordinate
- `anchorCell`: target coordinate or direction anchor
- `range`: maximum allowed distance
- `size`: shape dimension in grid cells
- `affectedCells`: resolved footprint after validation
- `result`: `pending`, `accepted`, or `rejected`
- `rejectionReason`: optional failure explanation

**Validation Rules**
- Shape must be one of the supported feature shapes
- Origin and anchor must lie on the map
- Affected cells must be derived deterministically by the engine
- Obstacles that block targeting remove blocked propagation cells where applicable
- Targeting must be legal under the current authoritative combat state

## RealtimeActionEvent

**Purpose**: Carries authoritative state changes or rejection outcomes between
server and clients.

**Fields**
- `eventId`: unique event identifier
- `eventType`: contract event name
- `encounterId`: related encounter
- `version`: authoritative encounter version after application
- `actionId`: associated request identifier when applicable
- `payload`: typed event-specific data
- `replaySafe`: whether duplicate delivery must be ignored

**Validation Rules**
- Event versions must be monotonic per encounter
- Duplicate `eventId` values must not apply state twice

## Relationship Notes

- `BattleMap` is the aggregate root for grid, obstacle, token, and combat data.
- `CombatState` coordinates which `Token` may submit turn-restricted actions.
- `MovementAction` and `TargetingTemplate` are validated against `BattleMap`,
  `Obstacle`, `Token`, and `CombatState`.
- `RealtimeActionEvent` communicates authoritative outcomes derived from engine
  validation and encounter version changes.
