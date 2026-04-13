---

description: "Task list for Tactical Battle Map System implementation"
---

# Tasks: Tactical Battle Map System

**Input**: Design documents from `/specs/001-tactical-battle-map/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Constitution-required tests are included. Engine, contract, and integration coverage MUST be written for tactical rules, authoritative state transitions, realtime contracts, and resynchronization behavior.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize the monorepo structure, tooling, and shared package wiring required by the implementation plan.

- [X] T001 Create the workspace structure in `apps/server`, `apps/web`, `packages/tactical-engine`, and `packages/shared-contracts`
- [X] T002 Initialize workspace package manifests and TypeScript project references in `package.json`, `tsconfig.base.json`, `apps/server/tsconfig.json`, `apps/web/tsconfig.json`, `packages/tactical-engine/tsconfig.json`, and `packages/shared-contracts/tsconfig.json`
- [X] T003 [P] Configure Vite and React app scaffolding in `apps/web/package.json`, `apps/web/vite.config.ts`, and `apps/web/src/main.tsx`
- [X] T004 [P] Configure Fastify server scaffolding in `apps/server/package.json`, `apps/server/src/app.ts`, and `apps/server/src/server.ts`
- [X] T005 [P] Configure workspace linting and formatting in `.gitignore`, `eslint.config.js`, and `prettier.config.cjs`
- [X] T006 [P] Configure Vitest and Playwright runners in `vitest.workspace.ts`, `apps/server/tests/vitest.config.ts`, `packages/tactical-engine/tests/vitest.config.ts`, and `apps/web/tests/playwright.config.ts`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build shared contracts, authoritative state scaffolding, and engine boundaries that every user story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T007 [P] Implement shared domain schemas for maps, tokens, combat state, movement actions, targeting templates, and realtime events in `packages/shared-contracts/src/domain.ts`
- [X] T008 [P] Implement shared HTTP and websocket payload schemas in `packages/shared-contracts/src/http.ts` and `packages/shared-contracts/src/realtime.ts`
- [X] T009 [P] Implement core grid coordinate, occupancy, and obstacle primitives in `packages/tactical-engine/src/grid/coordinates.ts`, `packages/tactical-engine/src/grid/grid-state.ts`, and `packages/tactical-engine/src/validation/obstacle-rules.ts`
- [X] T010 [P] Implement encounter versioning and idempotency helpers in `packages/tactical-engine/src/validation/versioning.ts` and `packages/tactical-engine/src/validation/action-idempotency.ts`
- [X] T011 Implement the in-memory encounter repository and snapshot assembly in `apps/server/src/modules/encounters/encounter-repository.ts` and `apps/server/src/modules/encounters/encounter-snapshot.ts`
- [X] T012 Implement websocket session bootstrap and authoritative broadcast plumbing in `apps/server/src/modules/realtime/socket-server.ts` and `apps/server/src/modules/realtime/broadcast.ts`
- [X] T013 Implement HTTP snapshot and resync routes from the contract in `apps/server/src/routes/encounter-routes.ts`
- [X] T014 Implement client session/bootstrap services in `apps/web/src/services/http-client.ts`, `apps/web/src/services/socket-client.ts`, and `apps/web/src/services/session-store.ts`
- [X] T015 Implement the shared battle map shell and authoritative state store in `apps/web/src/features/battle-map/battle-map-page.tsx`, `apps/web/src/features/battle-map/battle-map-store.ts`, and `apps/web/src/features/battle-map/battle-map-grid.tsx`
- [X] T016 Configure structured rejection/result handling and sync recovery hooks in `apps/server/src/modules/realtime/rejection-events.ts`, `apps/web/src/services/realtime-recovery.ts`, and `apps/web/src/features/battle-map/sync-status.tsx`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Move Tokens in Live Combat (Priority: P1) 🎯 MVP

**Goal**: Deliver deterministic, validated token movement with synchronized authoritative state across connected clients.

**Independent Test**: Start a shared encounter with two clients, submit legal and illegal movement actions for owned and unowned tokens, and verify authoritative positions converge on every client.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T017 [P] [US1] Add engine tests for grid occupancy, blocked paths, and alternating-cost diagonal movement in `packages/tactical-engine/tests/unit/movement-rules.test.ts`
- [X] T018 [P] [US1] Add contract tests for `movement.request`, `movement.applied`, and `action.rejected` flows in `apps/server/tests/contract/movement.contract.test.ts`
- [X] T019 [P] [US1] Add end-to-end movement synchronization coverage in `apps/web/tests/movement-sync.spec.ts`

### Implementation for User Story 1

- [X] T020 [P] [US1] Implement token and controller models in `packages/tactical-engine/src/grid/token-state.ts` and `packages/shared-contracts/src/tokens.ts`
- [X] T021 [P] [US1] Implement deterministic movement cost and path validation in `packages/tactical-engine/src/movement/path-cost.ts` and `packages/tactical-engine/src/movement/validate-movement.ts`
- [X] T022 [US1] Implement the authoritative movement service in `apps/server/src/modules/encounters/movement-service.ts`
- [X] T023 [US1] Implement websocket movement request handling in `apps/server/src/modules/realtime/movement-handler.ts`
- [X] T024 [US1] Implement token rendering and movement submission UI in `apps/web/src/features/battle-map/token-layer.tsx` and `apps/web/src/features/battle-map/use-movement-actions.ts`
- [X] T025 [US1] Implement movement rejection messaging and optimistic preview rollback in `apps/web/src/features/battle-map/movement-feedback.tsx` and `apps/web/src/features/battle-map/battle-map-store.ts`

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Run Turn-Based Combat (Priority: P2)

**Goal**: Reflect authoritative turn order and combat progression from LimiarControl while enforcing turn-based action restrictions on the map.

**Independent Test**: Load an encounter with initiative order, advance turns through LimiarControl, and verify every client reflects the same active combatant while out-of-turn actions are rejected.

### Tests for User Story 2

- [X] T026 [P] [US2] Add engine tests for combat state transitions and active-turn validation in `packages/tactical-engine/tests/unit/combat-state.test.ts`
- [X] T027 [P] [US2] Add contract tests for `combat.advance.request` and `combat.advanced` handling in `apps/server/tests/contract/combat.contract.test.ts`
- [X] T028 [P] [US2] Add end-to-end combat authority coverage in `apps/web/tests/combat-authority.spec.ts`

### Implementation for User Story 2

- [X] T029 [P] [US2] Implement combat state and initiative models in `packages/tactical-engine/src/combat/combat-state.ts` and `packages/shared-contracts/src/combat.ts`
- [X] T030 [US2] Implement LimiarControl combat advancement validation in `packages/tactical-engine/src/combat/advance-combat.ts`
- [X] T031 [US2] Implement authoritative combat update handling in `apps/server/src/modules/combat/combat-service.ts` and `apps/server/src/modules/realtime/combat-handler.ts`
- [X] T032 [US2] Enforce current-turn restrictions across tactical actions in `apps/server/src/modules/encounters/action-authorization.ts` and `apps/server/src/modules/encounters/movement-service.ts`
- [X] T033 [US2] Implement combat HUD and active-turn presentation in `apps/web/src/features/combat/combat-panel.tsx` and `apps/web/src/features/combat/use-combat-state.ts`

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Preview and Resolve Spell Targeting (Priority: P3)

**Goal**: Provide local spell area previews and authoritative affected-cell resolution for line, cone, sphere, and cube targeting without applying spell effects.

**Independent Test**: Preview each supported shape locally, submit legal and blocked targets, and verify the authoritative affected-cell footprint matches across clients without applying downstream effects.

### Tests for User Story 3

- [X] T034 [P] [US3] Add engine tests for line, cone, sphere, and cube resolution with obstacle blocking in `packages/tactical-engine/tests/unit/targeting-shapes.test.ts`
- [X] T035 [P] [US3] Add contract tests for `targeting.submit` and `targeting.resolved` events in `apps/server/tests/contract/targeting.contract.test.ts`
- [X] T036 [P] [US3] Add end-to-end targeting preview and resolution coverage in `apps/web/tests/targeting-resolution.spec.ts`

### Implementation for User Story 3

- [X] T037 [P] [US3] Implement targeting shape models and validators in `packages/tactical-engine/src/targeting/targeting-template.ts` and `packages/shared-contracts/src/targeting.ts`
- [X] T038 [US3] Implement deterministic shape resolution and obstacle blocking in `packages/tactical-engine/src/targeting/resolve-line.ts`, `packages/tactical-engine/src/targeting/resolve-cone.ts`, `packages/tactical-engine/src/targeting/resolve-sphere.ts`, and `packages/tactical-engine/src/targeting/resolve-cube.ts`
- [X] T039 [US3] Implement authoritative targeting resolution service in `apps/server/src/modules/encounters/targeting-service.ts`
- [X] T040 [US3] Implement websocket targeting request handling in `apps/server/src/modules/realtime/targeting-handler.ts`
- [X] T041 [US3] Implement local targeting preview state and shape overlays in `apps/web/src/features/targeting/targeting-preview-store.ts`, `apps/web/src/features/targeting/shape-overlay.tsx`, and `apps/web/src/features/targeting/use-targeting-actions.ts`
- [X] T042 [US3] Implement targeting result rendering and non-effect confirmation UX in `apps/web/src/features/targeting/targeting-result-panel.tsx`

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements and validation that affect multiple user stories

- [X] T043 [P] Document architecture, local development, and contract usage in `README.md` and `specs/001-tactical-battle-map/quickstart.md`
- [X] T044 Harden authorization and replay-safety edge cases in `apps/server/src/modules/encounters/action-authorization.ts`, `apps/server/src/modules/realtime/broadcast.ts`, and `packages/tactical-engine/src/validation/action-idempotency.ts`
- [X] T045 [P] Add reconnect and resync regression coverage in `apps/server/tests/integration/resync.integration.test.ts` and `apps/web/tests/reconnect-resync.spec.ts`
- [ ] T046 Run the full quickstart validation flow and record any required adjustments in `specs/001-tactical-battle-map/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel if staffed
  - Or sequentially in priority order (P1 -> P2 -> P3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - establishes the MVP
- **User Story 2 (P2)**: Depends on Foundational and reuses movement/action authorization from US1
- **User Story 3 (P3)**: Depends on Foundational and on US2 combat-state enforcement for turn-aware targeting validation

### Within Each User Story

- Constitution-required tests MUST be written and FAIL before implementation
- Shared models and schemas before engine rules
- Engine rules before server handlers
- Server handlers before web interaction flows
- Story complete before moving to the next priority slice

### Parallel Opportunities

- T003, T004, T005, and T006 can run in parallel during setup
- T007, T008, T009, and T010 can run in parallel during foundational work
- Within US1, T017, T018, and T019 can run in parallel; T020 and T021 can run in parallel
- Within US2, T026, T027, and T028 can run in parallel; T029 can start alongside test authoring
- Within US3, T034, T035, and T036 can run in parallel; T037 can run before T038 independently of web UI work
- T043 and T045 can run in parallel during polish

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Add engine tests for grid occupancy, blocked paths, and alternating-cost diagonal movement in packages/tactical-engine/tests/unit/movement-rules.test.ts"
Task: "Add contract tests for movement.request, movement.applied, and action.rejected flows in apps/server/tests/contract/movement.contract.test.ts"
Task: "Add end-to-end movement synchronization coverage in apps/web/tests/movement-sync.spec.ts"

# Launch the parallel implementation foundations:
Task: "Implement token and controller models in packages/tactical-engine/src/grid/token-state.ts and packages/shared-contracts/src/tokens.ts"
Task: "Implement deterministic movement cost and path validation in packages/tactical-engine/src/movement/path-cost.ts and packages/tactical-engine/src/movement/validate-movement.ts"
```

---

## Parallel Example: User Story 2

```bash
# Launch all tests for User Story 2 together:
Task: "Add engine tests for combat state transitions and active-turn validation in packages/tactical-engine/tests/unit/combat-state.test.ts"
Task: "Add contract tests for combat.advance.request and combat.advanced handling in apps/server/tests/contract/combat.contract.test.ts"
Task: "Add end-to-end combat authority coverage in apps/web/tests/combat-authority.spec.ts"
```

---

## Parallel Example: User Story 3

```bash
# Launch all tests for User Story 3 together:
Task: "Add engine tests for line, cone, sphere, and cube resolution with obstacle blocking in packages/tactical-engine/tests/unit/targeting-shapes.test.ts"
Task: "Add contract tests for targeting.submit and targeting.resolved events in apps/server/tests/contract/targeting.contract.test.ts"
Task: "Add end-to-end targeting preview and resolution coverage in apps/web/tests/targeting-resolution.spec.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Stop and validate synchronized authoritative movement before expanding scope

### Incremental Delivery

1. Setup the workspace and authoritative infrastructure
2. Deliver User Story 1 as the first playable tactical slice
3. Add User Story 2 to enforce authoritative combat progression
4. Add User Story 3 for local preview plus authoritative target resolution
5. Finish with reconnect hardening, documentation, and regression coverage

### Parallel Team Strategy

1. One engineer handles workspace/tooling while another starts shared contracts during Phase 1
2. After Foundational completes:
   - Engineer A: User Story 1 movement flow
   - Engineer B: User Story 2 combat authority
   - Engineer C: User Story 3 targeting system
3. Rejoin for polish, reconnect testing, and quickstart validation

---

## Notes

- All tasks follow the required checklist format with task ID, optional `[P]`, story label where required, and file paths
- User stories remain independently testable, with constitution-required tests written before implementation
- The suggested MVP scope is User Story 1 only
- Avoid introducing persistence, spell effect resolution, or client-authoritative state changes in this feature slice
