# Quickstart: Tactical Battle Map System

## Goal

Validate the first implementation slice for deterministic movement, combat turn
progression, spell targeting resolution, and reconnect safety.

## Prerequisites

- Install project dependencies
- Start the backend service
- Start the web client
- Open two browser clients connected to the same session
- Ensure a LimiarControl actor is available for combat progression

## Local Project Layout

- `apps/server` hosts the authoritative HTTP and websocket services
- `apps/web` hosts the browser client and local preview UI
- `packages/tactical-engine` contains deterministic movement, combat, and targeting rules
- `packages/shared-contracts` contains shared schemas used across tests, server, and client

## Validation Flow

### 1. Load an encounter

1. Open the battle map in both browser clients.
2. Verify both clients render the same tokens, obstacles, and combat state.

### 2. Validate authoritative movement

1. From a player-controlled client, submit a legal move for an owned token.
2. Verify the server accepts the move and both clients show the same final cell.
3. Submit an illegal move through a blocked or occupied cell.
4. Verify the move is rejected and both clients retain the previous authoritative state.

### 3. Validate combat authority

1. Start an encounter with an initiative order.
2. Advance the turn through LimiarControl.
3. Verify both clients show the same active combatant and round count.
4. Attempt an out-of-turn action from a player token.
5. Verify the action is rejected without changing shared state.

### 4. Validate targeting rules

1. Preview a supported targeting shape locally.
2. Confirm that the preview does not change authoritative state on the other client.
3. Submit the target for validation.
4. Verify both clients receive the same affected-cell footprint.
5. Repeat with an obstacle blocking propagation and verify blocked cells are excluded.

### 5. Validate reconnect and replay safety

1. Disconnect one client during an active encounter.
2. Apply one or more authoritative actions from the remaining client or LimiarControl.
3. Reconnect the disconnected client.
4. Verify it resynchronizes to the latest authoritative snapshot within the expected time window.
5. Resend a previously acknowledged action identifier and verify no duplicate state change occurs.

## Expected Outcomes

- Movement, combat advancement, and targeting outcomes match across clients
- Invalid actions are rejected without divergence
- Targeting stops at affected-cell resolution and does not apply spell effects
- Reconnect restores the latest authoritative state
