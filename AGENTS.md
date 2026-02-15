# Repository Guidelines (LimiarControl)

## Project Structure & Module Organization
- `src/` is organized by slices: `app/`, `pages/`, `features/`, `entities/`, `widgets/`, `shared/`, `test/`.
- `src/pages/`: route-level composition only. Pages should be thin (layout + wiring).
- `src/features/`: user-facing capabilities (behavior + feature-specific UI + hooks + API calls).
- `src/entities/`: domain types/schemas/mappers (no fetching, no UI).
- `src/shared/`: reusable “dumb” UI and generic utilities (must not depend on features/pages).
- `src/widgets/`: larger reusable screen blocks composed of shared UI + features.
- `src/test/`: test helpers (factories, MSW).

### Import rules (keep boundaries)
- `pages` may import from `widgets`, `features`, `entities`, `shared`.
- `features` may import from `entities` and `shared` (avoid importing from `pages` or other features unless via a well-defined public API).
- `entities` should not import from `features`, `pages`, or `shared/ui`.
- `shared` must not import from `features`, `entities`, or `pages`.

### Public API exports
- Prefer `index.ts` barrel exports per slice/folder for clean imports.
- Only export what is intended to be used by other slices.

## File size & modularity
- Keep files small and focused (target <200 lines).
- Split large components into smaller components/hooks/utils.
- Avoid “god components” and large pages with mixed concerns.

## Build, Test, and Development Commands
- Install: `npm install`
- Dev: `npm run dev` (expected once Vite is set up)
- Build: `npm run build`
- Preview: `npm run preview`
- Lint/format: `npm run lint`, `npm run format` (add when configured)
- When adding scripts, document them in `README.md`.

## Coding Style & Naming Conventions
- TypeScript + React.
- Pages: `PascalCase` folders, `*Page` suffix (e.g., `ShopPage`).
- Features: `kebab-case` folders (e.g., `npc-generator`).
- Components: `PascalCase`. Functions/vars: `camelCase`.
- Prefer Zod schemas for runtime validation (placed under `entities/*`).

## Security Guidelines
- Frontend env uses only `VITE_*`. Do not commit `.env`. Never put secrets in frontend env.
- Do not store auth tokens in `localStorage`/`sessionStorage`. Prefer HttpOnly cookies (when auth is implemented).
- Enforce permissions based on role (MASTER/PLAYER) in the backend (UI checks are not sufficient).

## Testing Guidelines
- Keep tests close to the code they cover (prefer `*.test.ts(x)` near features/components).
- Use `src/test/` for shared test utilities (factories, MSW handlers).
- Suggested runner: Vitest + Testing Library (configure when ready).

## Commit Guidelines
- Use concise, imperative subjects (e.g., `Add shop item grid`).
- Keep commits focused and avoid mixing unrelated changes.