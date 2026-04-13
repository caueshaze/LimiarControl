# HTTP API Contract: Tactical Battle Map System

## Purpose

HTTP endpoints bootstrap encounter data and recover authoritative state after
reconnect. Mutating tactical actions remain primarily realtime requests, while
HTTP provides session-safe reads and resync entry points.

## Endpoints

### `GET /sessions/:sessionId/encounter`

**Purpose**: Fetch the latest authoritative encounter snapshot for initial load
or recovery.

**Response**

```json
{
  "sessionId": "sess_123",
  "battleMap": {
    "id": "map_1",
    "name": "Goblin Ambush",
    "gridWidth": 20,
    "gridHeight": 20,
    "terrainVersion": 3
  },
  "combatState": {
    "status": "active",
    "roundNumber": 2,
    "turnIndex": 4,
    "activeCombatantId": "cmb_4",
    "initiativeOrder": ["cmb_1", "cmb_2", "cmb_3", "cmb_4"],
    "version": 18
  },
  "tokens": [],
  "obstacles": []
}
```

**Rules**
- Response is always authoritative
- Snapshot includes encounter `version` for subsequent realtime sequencing

### `POST /sessions/:sessionId/resync`

**Purpose**: Request a full authoritative resynchronization after divergence or reconnect.

**Request**

```json
{
  "lastKnownVersion": 16,
  "clientInstanceId": "client_abc"
}
```

**Response**

```json
{
  "resynced": true,
  "snapshotVersion": 18
}
```

**Rules**
- The backend may return the same latest state even when the client is already current
- The response indicates the authoritative version used for subsequent realtime events

## Error Semantics

- `404` when the session or encounter does not exist
- `403` when the caller is not authorized for the session
- `409` when the request references a session state that cannot be reconciled without a full reload
