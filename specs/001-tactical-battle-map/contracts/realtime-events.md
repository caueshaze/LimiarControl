# Realtime Event Contract: Tactical Battle Map System

## Transport

Socket-based bidirectional events with acknowledgement for authoritative action
requests. Events are divided into:
- Authoritative action requests sent client -> server
- Authoritative state updates sent server -> client
- Ephemeral preview events kept client-local and not transmitted as authoritative state

## Client -> Server Events

### `movement.request`

```json
{
  "actionId": "act_move_001",
  "sessionId": "sess_123",
  "tokenId": "tok_7",
  "path": [{"x": 4, "y": 7}, {"x": 5, "y": 8}],
  "knownVersion": 18
}
```

**Rules**
- Server validates authorization, current authoritative combat state, turn restrictions,
path continuity, diagonal alternating cost, occupancy, and obstacles
- Duplicate `actionId` must not apply movement twice

### `combat.advance.request`

```json
{
  "actionId": "act_turn_001",
  "sessionId": "sess_123",
  "knownVersion": 18,
  "requestedBy": "limiarControl"
}
```

**Rules**
- Only LimiarControl or a backend process on its authority may advance combat state
- Player and GM tactical actions must be validated against the latest authoritative combat state before acceptance

### `targeting.submit`

```json
{
  "actionId": "act_target_001",
  "sessionId": "sess_123",
  "tokenId": "tok_7",
  "shape": "cone",
  "originCell": {"x": 5, "y": 8},
  "anchorCell": {"x": 8, "y": 8},
  "range": 6,
  "size": 3,
  "knownVersion": 19
}
```

**Rules**
- Server validates permission, current turn, range, shape geometry, and obstacle blocking rules
- Successful validation resolves only the affected-cell footprint for this feature

## Server -> Client Events

### `encounter.snapshot`

```json
{
  "eventId": "evt_snapshot_020",
  "sessionId": "sess_123",
  "version": 20,
  "battleMap": {},
  "combatState": {},
  "tokens": [],
  "obstacles": []
}
```

**Purpose**: Full authoritative snapshot for initial join or resync.

### `movement.applied`

```json
{
  "eventId": "evt_move_021",
  "actionId": "act_move_001",
  "sessionId": "sess_123",
  "version": 21,
  "tokenId": "tok_7",
  "position": {"x": 5, "y": 8},
  "pathCostUnits": 10
}
```

**Notes**
- `pathCostUnits` represents deterministic movement cost units produced by the engine, not pixels or animation distance

### `combat.advanced`

```json
{
  "eventId": "evt_turn_022",
  "actionId": "act_turn_001",
  "sessionId": "sess_123",
  "version": 22,
  "roundNumber": 2,
  "turnIndex": 5,
  "activeCombatantId": "cmb_5"
}
```

### `targeting.resolved`

```json
{
  "eventId": "evt_target_023",
  "actionId": "act_target_001",
  "sessionId": "sess_123",
  "version": 23,
  "tokenId": "tok_7",
  "shape": "cone",
  "affectedCells": [{"x": 6, "y": 8}, {"x": 7, "y": 8}]
}
```

### `action.rejected`

```json
{
  "eventId": "evt_reject_024",
  "actionId": "act_move_001",
  "sessionId": "sess_123",
  "version": 23,
  "reason": "blocked_path",
  "details": "Path crosses an occupied cell"
}
```

## Replay and Resync Rules

- Every authoritative request carries an `actionId` used for idempotent processing
- Every authoritative server event carries a monotonic `version`
- Clients ignore already-applied versions and request `encounter.snapshot` when they detect a gap or reconnect
- Preview overlays remain local UI state and are never broadcast as authoritative events
