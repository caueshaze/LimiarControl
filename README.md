# LimiarControl

LimiarControl is a real-time TTRPG campaign and session manager for Game Masters and players. The project combines a React frontend, a FastAPI backend, PostgreSQL persistence, and Centrifugo for live session events.

It is designed around party-based play: players join a party, create their character sheet, wait in a lobby when the GM opens a session, and then move into a live board where rolls, shop actions, inventory changes, and session updates happen in real time.

## Highlights

- Party-based campaigns with invites and player membership status
- Character sheet creation and play mode
- Real-time lobby flow before a session starts
- GM dashboard for shop control, roll requests, and live inventory inspection
- In-session shop with buy and sell flows
- Player inventory and session activity views
- GM grants for currency and items during an active session
- PostgreSQL-backed state with Alembic migrations
- Centrifugo-powered real-time events for session lifecycle and play updates

## Stack

- Frontend: React 19, TypeScript, Vite, Tailwind CSS
- Backend: FastAPI, SQLModel, Alembic
- Database: PostgreSQL 16
- Real-time: Centrifugo
- Local infrastructure: Docker Compose

## Repository layout

```text
.
├── apps/
│   ├── control-web/         React frontend do LimiarControl
│   ├── control-server/      FastAPI backend do LimiarControl
│   ├── map-web/             React frontend do LimiarMap
│   └── map-server/          Fastify + Centrifugo backend do LimiarMap
├── packages/
│   ├── shared-contracts/    Contratos compartilhados para integracao
│   └── tactical-engine/     Engine tatica pura
├── centrifugo/              Centrifugo config
├── Base/                    Base RPG datasets used by the app
├── docker-compose.yml       Local development infra
├── docker-compose.lab.yml   Homologation stack
├── docker-compose.prod.yml  Production-like stack
└── package.json             Workspaces e scripts do monorepo
```

## Core flow

1. The GM creates a campaign and one or more parties.
2. Players join a party and create their character sheets.
3. Starting equipment from the character sheet is seeded into the player inventory.
4. The GM starts a lobby and sees player readiness in real time.
5. When the session starts:
   - players are redirected to the board
   - the GM stays in the GM dashboard
6. During the session the GM can:
   - open or close the shop
   - request rolls
   - inspect player inventories
   - grant items or currency to players
7. Players receive state updates live through Centrifugo events.

## Environments

### Development

Recommended for day-to-day work. Run infrastructure in Docker and keep frontend/backend hot reload on the host.

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Centrifugo: `ws://localhost:8001/connection/websocket`
- Compose file: [docker-compose.yml](/home/caue/LimiarControl/docker-compose.yml)

### Lab

Recommended for pre-merge validation and homologation. This stack is isolated from production and uses its own ports, containers, network, and database volume.

- App + API: `http://127.0.0.1:8002`
- Centrifugo: `ws://127.0.0.1:8003/connection/websocket`
- Compose file: [docker-compose.lab.yml](/home/caue/LimiarControl/docker-compose.lab.yml)
- Env example: [.env.lab.example](/home/caue/LimiarControl/.env.lab.example)

### Production

Production now uses the single-container app stack for frontend + backend, with Centrifugo and Postgres alongside it.

- App + API: `http://127.0.0.1:8000`
- Centrifugo: `ws://127.0.0.1:8001/connection/websocket`
- Compose file: [docker-compose.prod.yml](/home/caue/LimiarControl/docker-compose.prod.yml)

## Local development

### Prerequisites

- Node.js 18+
- Python 3.11+
- Docker and Docker Compose

### 1. Configure environment

Copy the root env example and adjust if needed:

```bash
cp .env.example .env
```

The defaults in `.env.example` work out of the box for local development.

### 2. Start infrastructure

Start PostgreSQL, MinIO, and Centrifugo:

```bash
docker compose up -d
```

### 3. Backend setup

```bash
cd apps/control-server
python -m venv .venv
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e .
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend reads the repository root `.env` automatically (python-dotenv). The relevant variables for local development are already set in `.env.example`.

### 4. Map server (LimiarMap)

Required when `LIMIAR_MAP_ENABLED=true` (default). From the repository root:

```bash
npm run dev:map
```

This starts both the Fastify map server (port 3000) and the map frontend (port 5174).

To run only the map server without the map frontend:

```bash
npm run dev:map:server
```

### 5. Install dependencies and start the frontend

From the repository root:

```bash
npm install
npm run dev:control
```

### 6. Open the app

- Control frontend: `http://localhost:5173`
- Map frontend: `http://localhost:5174`
- API docs: `http://localhost:8000/docs`
- API health: `http://localhost:8000/health`
- MinIO console: `http://localhost:9001` (minioadmin / minioadmin)

### 7. Validate the production-like stack locally

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Expected endpoints in this mode:

- App + API: `http://127.0.0.1:8000/`
- API health: `http://127.0.0.1:8000/health`
- Centrifugo websocket: `ws://localhost:8001/connection/websocket`

### 8. Validate the lab stack locally

```bash
cp .env.lab.example .env.lab
docker compose --env-file .env.lab -f docker-compose.lab.yml up -d --build
```

Expected endpoints in this mode:

- App + API: `http://127.0.0.1:8002/`
- API health: `http://127.0.0.1:8002/health`
- Centrifugo websocket: `ws://127.0.0.1:8003/connection/websocket`

## Environment files

### Root `.env`

Use [.env.example](.env.example) as the starting point:

```bash
cp .env.example .env
```

All defaults work out of the box for local development. The file covers PostgreSQL, MinIO, Centrifugo, JWT, CORS, and Vite build variables.

### Lab `.env`

Use [.env.lab.example](.env.lab.example) as the starting point for homologation:

```bash
cp .env.lab.example .env.lab
```

## Useful commands

### Frontend

```bash
npm run dev:control
npm run build:control
npm run preview -w apps/control-web
npx tsc --noEmit
```

### Production with single-container app

The main `Dockerfile` already packages frontend + backend in the same container. In production,
FastAPI serves the Vite `dist/` directly.

Before bringing the production stack up, set the root `.env` with real values:

```env
APP_ENV=production
POSTGRES_USER=app_user
POSTGRES_PASSWORD=use-uma-senha-forte
POSTGRES_DB=limiarcontrol
JWT_SECRET=use-um-segredo-forte
CENTRIFUGO_API_KEY=use-uma-chave-forte
CENTRIFUGO_TOKEN_SECRET=use-um-segredo-forte
CORS_ORIGIN=https://seu-dominio.com
CENTRIFUGO_ALLOWED_ORIGINS=https://seu-dominio.com
DOCKER_VITE_API_BASE_URL=/api
DOCKER_VITE_CENTRIFUGO_URL=wss://rt.seu-dominio.com/connection/websocket
```

Suba com:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

If `POSTGRES_USER=postgres` and `POSTGRES_PASSWORD=postgres` remain in `.env`, the backend
will abort in production with `DATABASE_URL must use strong credentials in production`.

### Lab stack

The lab stack is intentionally isolated from production:

- app + api lab: `127.0.0.1:8002`
- realtime lab: `127.0.0.1:8003`
- containers: `limiar-lab-api`, `limiar-lab-db`, `limiar-lab-centrifugo`
- network: `limiar_lab_internal`
- database volume: `limiar_lab_db`

Start it with:

```bash
docker compose --env-file .env.lab -f docker-compose.lab.yml up -d --build
```

### Backend

```bash
cd apps/control-server
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
python -m py_compile app/api/routes/sessions/*.py
```

### Base catalog seed

After running migrations, the runtime uses database + JSON seed as the official base-item catalog flow.

Bootstrap or replace the base item catalog with the repository seed:

```bash
apps/control-server/.venv/bin/python scripts/import_base_items_json.py --input Base/base_items.seed.json --replace
```

Export the current database catalog back to the repository seed format:

```bash
apps/control-server/.venv/bin/python scripts/export_base_items_json.py --output Base/base_items.seed.json
```

Bootstrap or replace the base spell catalog with the repository seed:

```bash
apps/control-server/.venv/bin/python scripts/import_base_spells_json.py --input Base/base_spells.seed.json --replace
```

Notes:

- `Base/base_items.seed.json` is the official bootstrap/backup file for the base item catalog
- `Base/base_spells.seed.json` is the official bootstrap/backup file for the base spell catalog
- the database is the source of truth at runtime
- old CSV files may remain in `Base/` for editorial reference, but they are no longer part of the main runtime flow

Current validated result in the local dev database:

- `base_item`: 112 rows
- `base_item_alias`: 243 rows
- `base_spell`: 319 rows
- `base_spell_alias`: 319 rows

## Real-time notes

The app relies on Centrifugo for most live updates. Session and campaign clients subscribe to realtime channels and react to events such as:

- `session_lobby`
- `player_joined_lobby`
- `session_started`
- `session_closed`
- `shop_opened`
- `shop_closed`
- `roll_requested`
- `dice_rolled`
- `shop_purchase_created`
- `shop_sale_created`
- `session_state_updated`
- `gm_granted_currency`
- `gm_granted_item`

Some screens still keep short polling fallbacks, but the primary source of truth during play is the realtime event stream.

## Notes for contributors

- Frontend code is organized by slices under `apps/control-web/src/`
- Pages should stay thin and compose feature modules
- Backend routes live under `apps/control-server/app/api/routes/`
- Always run `alembic upgrade head` after pulling schema changes
- Do not commit local `.env` files or generated build artifacts

## License

MIT. See [LICENSE](LICENSE).
