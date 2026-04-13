# Research: Tactical Battle Map System

## Decision: Use a web application with an authoritative backend and a shared tactical engine

**Rationale**: The feature requires realtime multiplayer synchronization across
clients and explicit separation between visualization and authoritative rules. A
browser client plus authoritative server matches the usage model, while a shared
engine package keeps tactical logic framework-agnostic and testable.

**Alternatives considered**:
- Native desktop client: rejected because the feature scope does not require
  platform-specific capabilities.
- Client-authoritative peer-to-peer model: rejected because it conflicts with
  the constitution and increases divergence risk.

## Decision: Use TypeScript across frontend, backend, and shared packages

**Rationale**: A single language across the stack reduces schema drift between
contracts, frontend state handling, and backend validation while making the
shared engine package practical from day one.

**Alternatives considered**:
- Separate backend and frontend languages: rejected because it adds integration
  overhead without helping the initial feature scope.
- Backend-only shared engine: rejected because the client still benefits from
  typed preview helpers and contract reuse.

## Decision: Model realtime transport with Fastify + Socket.IO

**Rationale**: The system needs request/response bootstrap flows plus persistent
realtime event streams. Fastify provides a lean HTTP layer for session and map
bootstrap, while Socket.IO provides structured event channels, acknowledgements,
and reconnect support suitable for authoritative synchronization.

**Alternatives considered**:
- Pure REST polling: rejected because it is a poor fit for low-latency shared
  tactical state.
- Raw WebSocket handling: rejected for the initial release because it would
  require more custom connection and retry management before feature value is delivered.

## Decision: Keep encounter state in memory for the initial release

**Rationale**: The first feature slice targets live multiplayer encounters with
one active shared session at a time. In-memory storage keeps the initial design
simple and allows focus on correctness, rules, and synchronization before
introducing persistence complexity.

**Alternatives considered**:
- Relational database persistence: rejected because the first release does not
  require long-term encounter recovery.
- Client-side persistence: rejected because it conflicts with server authority.

## Decision: Implement movement, combat, and targeting as explicit engine systems

**Rationale**: The constitution forbids one-off ability logic. Separate engine
systems for grid occupancy, alternating-cost movement, turn progression,
obstacle evaluation, and targeting shapes provide deterministic behavior and
clear test boundaries.

**Alternatives considered**:
- Monolithic rules service: rejected because it would blur responsibilities and
  complicate testing.
- Spell-specific handlers: rejected because they conflict with explicit rule
  modeling requirements.

## Decision: Treat targeting previews as client-local and target confirmation as authoritative

**Rationale**: Previews need fast interaction but must not pollute persistent
state. Keeping previews local while sending only confirmed targeting requests to
the backend preserves responsiveness without compromising authority boundaries.

**Alternatives considered**:
- Persisted preview state: rejected because it adds noise to authoritative
  synchronization.
- No preview support: rejected because the feature explicitly requires area preview.

## Decision: Encode replay safety through action identifiers and encounter versions

**Rationale**: Duplicate or delayed events must not apply the same state change
twice. Action identifiers paired with monotonic encounter versions give the
server and clients a simple basis for de-duplication, ordering, and resync.

**Alternatives considered**:
- Timestamp-only ordering: rejected because clocks are not reliable enough for
  authoritative sequencing.
- Best-effort duplicate tolerance without identifiers: rejected because it makes
  debugging and replay safety weaker.

## Decision: Validate the system with engine, contract, and end-to-end tests

**Rationale**: Core tactical rules need deterministic unit coverage, while
realtime synchronization and authority boundaries require contract and browser
level verification. This testing mix matches the constitution and the feature risk.

**Alternatives considered**:
- End-to-end tests only: rejected because they would be too coarse for rules debugging.
- Unit tests only: rejected because they would miss transport and resync behavior.
