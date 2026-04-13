# Implementation Plan: Tactical Battle Map System

**Branch**: `001-tactical-battle-map` | **Date**: 2026-03-31 | **Spec**: [/home/caue/LimiarMap/specs/001-tactical-battle-map/spec.md](/home/caue/LimiarMap/specs/001-tactical-battle-map/spec.md)
**Input**: Feature specification from `/specs/001-tactical-battle-map/spec.md`

## Summary

Build a realtime tactical battle map as a web application with a server-authoritative
backend, a shared framework-agnostic tactical engine, and a client that renders
authoritative state plus non-authoritative previews. The first implementation
slice covers deterministic grid movement, obstacle/collision validation,
combat-state progression sourced from LimiarControl, and validated spell
targeting previews/resolution for line, cone, sphere, and cube without applying
downstream spell effects.

## Technical Context

**Language/Version**: TypeScript 5.x on Node.js 22; React 19 for the client  
**Primary Dependencies**: Fastify, Socket.IO, React, Vite, Zod, Vitest, Playwright  
**Storage**: In-memory encounter state for the initial release, with reconnect and 
resync support limited to the lifetime of the running server process 
**Testing**: Vitest for engine/unit and contract tests; Playwright for end-to-end synchronization flows  
**Target Platform**: Linux-hosted web service with modern desktop and tablet browsers  
**Project Type**: Web application with frontend, backend, and shared engine packages  
**Performance Goals**: 95% of valid actions visible to all connected clients within 1 second; reconnect resync within 3 seconds  
**Constraints**: Server-authoritative state only; deterministic grid rules; diagonal movement with alternating cost; obstacle blocking for spell propagation where applicable; targeting only for spell handling in this feature  
**Scale/Scope**: Single shared encounter per session, dozens of tokens per encounter, small-group multiplayer play

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Authoritative owner of gameplay state: backend encounter service and shared engine rules. No client path finalizes movement, combat state, or targeting outcomes without server validation.
- Deterministic grid resolution: all movement, occupancy, area, range, and obstacle calculations execute through shared engine primitives with no client-only rule forks.
- Explicit rule systems: movement, targeting shapes, combat turns, and obstacle interaction are modeled as reusable systems rather than spell-specific handlers.
- Realtime event contracts: websocket events distinguish authoritative mutations from ephemeral previews and define idempotent sequencing or replay handling.
- Permissions: player actions are limited to owned tokens, GM retains broad control, and LimiarControl exclusively advances combat turns while LimiarMap validates tactical actions against that authoritative combat state.
- Engine boundary: tactical rules live in a shared package independent of React, Fastify, and Socket.IO; validation is covered by engine, contract, and end-to-end tests.
- Fail-safe sync: reconnect and divergence paths trigger full authoritative resync from the backend.

Post-design review: PASS. Planned artifacts preserve server authority, deterministic grid logic, explicit contracts, engine isolation, and replay-safe synchronization.

## Project Structure

### Documentation (this feature)

```text
specs/001-tactical-battle-map/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── http-api.md
│   └── realtime-events.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/
├── server/
│   ├── src/
│   │   ├── modules/
│   │   │   ├── encounters/
│   │   │   ├── combat/
│   │   │   └── realtime/
│   │   └── routes/
│   └── tests/
│       ├── contract/
│       └── integration/
└── web/
    ├── src/
    │   ├── features/
    │   │   ├── battle-map/
    │   │   ├── combat/
    │   │   └── targeting/
    │   └── services/
    └── tests/

packages/
├── tactical-engine/
│   ├── src/
│   │   ├── combat/
│   │   ├── grid/
│   │   ├── movement/
│   │   ├── targeting/
│   │   └── validation/
│   └── tests/
│       └── unit/
└── shared-contracts/
    └── src/
```

**Structure Decision**: Use a web-application layout with `apps/server` for
authoritative state and realtime delivery, `apps/web` for visualization and
input capture, `packages/tactical-engine` for framework-agnostic deterministic
rules, and `packages/shared-contracts` for event/payload schemas reused across
client and server.

## Complexity Tracking

No constitution violations currently require justification.
