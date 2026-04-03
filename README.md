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
- Local infrastructure: Docker Compose for PostgreSQL and Centrifugo

## Repository layout

```text
.
├── src/                     Frontend application
│   ├── app/                 App config and routes
│   ├── entities/            Domain types and schemas
│   ├── features/            Feature modules
│   ├── pages/               Route-level pages
│   ├── shared/              Shared UI, API clients, realtime helpers
│   └── widgets/             Composed UI blocks
├── server_py/               FastAPI backend
│   ├── app/
│   │   ├── api/routes/      HTTP routes
│   │   ├── models/          SQLModel models
│   │   ├── schemas/         Pydantic schemas
│   │   └── services/        Backend services
│   └── alembic/             Database migrations
├── centrifugo/              Centrifugo config
├── Base/                    Base RPG datasets used by the app
└── docker-compose.yml       Local development services
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

## Local development

### Prerequisites

- Node.js 18+
- Python 3.11+
- Docker and Docker Compose

### 1. Start infrastructure

Start PostgreSQL and Centrifugo:

```bash
docker compose up -d db centrifugo
```

### 2. Backend setup

```bash
cd server_py
python -m venv .venv
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e .
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload
```

Use the repository root `.env` with localhost values when running FastAPI directly on your machine:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=limiarcontrol
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/limiarcontrol
PORT=3000
CORS_ORIGIN=http://localhost:5173,http://127.0.0.1:5173
CENTRIFUGO_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000
APP_ENV=development
AUTO_MIGRATE=true
JWT_SECRET=dev-secret-change-me
CENTRIFUGO_API_URL=http://localhost:8001/api
CENTRIFUGO_API_KEY=dev-api-key
CENTRIFUGO_TOKEN_SECRET=dev-secret-change-me
CENTRIFUGO_TOKEN_HMAC_SECRET_KEY=dev-secret-change-me
CENTRIFUGO_PUBLIC_URL=ws://localhost:8001/connection/websocket
```

### 3. Frontend setup

From the repository root:

```bash
npm install
npm run dev
```

### 4. Open the app

- Frontend: `http://localhost:5173`
- API docs: `http://localhost:3000/docs`
- API health: `http://localhost:3000/health`

### 5. Teste o stack em container único

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Endpoints esperados nesse modo:

- App + API: `http://127.0.0.1:8000/`
- API health: `http://127.0.0.1:8000/health`
- Centrifugo websocket: `ws://localhost:8001/connection/websocket`

## Environment files

### Root `.env`

Default example:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=limiarcontrol
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/limiarcontrol
PORT=3000
CORS_ORIGIN=http://localhost:5173,http://127.0.0.1:5173
CENTRIFUGO_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000
APP_ENV=development
AUTO_MIGRATE=true
JWT_SECRET=dev-secret-change-me
CENTRIFUGO_API_URL=http://localhost:8001/api
CENTRIFUGO_API_KEY=dev-api-key
CENTRIFUGO_TOKEN_SECRET=dev-secret-change-me
CENTRIFUGO_TOKEN_HMAC_SECRET_KEY=dev-secret-change-me
CENTRIFUGO_PUBLIC_URL=ws://localhost:8001/connection/websocket
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=
VITE_APP_ENV=development
VITE_API_BASE_URL=/api
VITE_CENTRIFUGO_URL=ws://localhost:8001/connection/websocket
VITE_ENABLE_MUSIC=true
VITE_ENABLE_MAPS=true
DOCKER_VITE_API_BASE_URL=/api
DOCKER_VITE_CENTRIFUGO_URL=ws://localhost:8001/connection/websocket
DOCKER_VITE_ENABLE_MUSIC=true
DOCKER_VITE_ENABLE_MAPS=true
```

## Useful commands

### Frontend

```bash
npm run dev
npm run build
npm run preview
npx tsc --noEmit
```

### Produção com container único

O `Dockerfile` principal já empacota frontend + backend no mesmo container. Em produção,
o FastAPI serve o `dist/` do Vite diretamente.

Antes de subir o stack de produção, ajuste o `.env` da raiz com valores reais:

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

Se `POSTGRES_USER=postgres` e `POSTGRES_PASSWORD=postgres` continuarem no `.env`, o backend
vai abortar em produção com `DATABASE_URL must use strong credentials in production`.

### Backend

```bash
cd server_py
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload
python -m py_compile app/api/routes/sessions/*.py
```

### Base catalog seed

After running migrations, the runtime uses database + JSON seed as the official base-item catalog flow.

Bootstrap or replace the base item catalog with the repository seed:

```bash
server_py/.venv/bin/python scripts/import_base_items_json.py --input Base/base_items.seed.json --replace
```

Export the current database catalog back to the repository seed format:

```bash
server_py/.venv/bin/python scripts/export_base_items_json.py --output Base/base_items.seed.json
```

Notes:

- `Base/base_items.seed.json` is the official bootstrap/backup file for the base item catalog
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

- Frontend code is organized by slices under `src/`
- Pages should stay thin and compose feature modules
- Backend routes live under `server_py/app/api/routes/`
- Always run `alembic upgrade head` after pulling schema changes
- Do not commit local `.env` files or generated build artifacts

## License

MIT. See [LICENSE](LICENSE).
