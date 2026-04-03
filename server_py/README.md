# FastAPI Server

## Requirements
- Python 3.11+
- Docker (for Postgres and Centrifugo)

## Recommended workflows

### Development

Use the root [docker-compose.yml](/home/caue/LimiarControl/docker-compose.yml) for infrastructure and run FastAPI locally with reload.

### Lab

Use [docker-compose.lab.yml](/home/caue/LimiarControl/docker-compose.lab.yml) when you want an isolated homologation stack before merging to `main`.

### Production-like

Use [docker-compose.prod.yml](/home/caue/LimiarControl/docker-compose.prod.yml) when you want to validate the single-container app stack locally or on a server.

## Run Postgres
```bash
docker compose up -d
```

This starts PostgreSQL on port `5432` and Centrifugo on port `8001`.

## Install deps
```bash
cd server_py
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Use the repository root `.env`:

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
CENTRIFUGO_PUBLIC_URL=ws://localhost:8001/connection/websocket
CENTRIFUGO_TOKEN_SECRET=dev-secret-change-me
CENTRIFUGO_TOKEN_HMAC_SECRET_KEY=dev-secret-change-me
```

## Run migrations
```bash
cd server_py
alembic upgrade head
```

In development, the API now runs `alembic upgrade head` automatically on startup by default.
Set `AUTO_MIGRATE=false` if you prefer fail-fast behavior instead of automatic upgrades.

## Seed base catalogs

After the schema is up to date, bootstrap the base catalogs from the repository JSON seeds.

Items import:

```bash
server_py/.venv/bin/python scripts/import_base_items_json.py --input Base/base_items.seed.json --replace
```

Items export:

```bash
server_py/.venv/bin/python scripts/export_base_items_json.py --output Base/base_items.seed.json
```

Spells import:

```bash
server_py/.venv/bin/python scripts/import_base_spells_json.py --input Base/base_spells.seed.json --replace
```

Notes:

- `Base/base_items.seed.json` is the official bootstrap/backup file for base items
- `Base/base_spells.seed.json` is the official bootstrap/backup file for base spells
- the runtime source of truth is the database
- legacy CSV files are no longer part of the main runtime flow

Validated local result:

- `base_item`: 112 rows
- `base_item_alias`: 243 rows
- `base_spell`: 319 rows
- `base_spell_alias`: 319 rows

## Run the API (port 3000)
```bash
cd server_py
uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload
```

## Run lab locally

Use the lab env example from the repo root:

```bash
cp .env.lab.example .env.lab
docker compose --env-file .env.lab -f docker-compose.lab.yml up -d --build
```

Endpoints:

- Frontend: `http://127.0.0.1:3001`
- API health: `http://127.0.0.1:8002/health`
- Centrifugo: `ws://127.0.0.1:8003/connection/websocket`

## Combat docs

- Phase 3A spell-combat notes: [docs/combat_spells_phase_3a.md](./docs/combat_spells_phase_3a.md)

## Curl examples
```bash
curl http://localhost:3000/api/campaigns

curl -X POST http://localhost:3000/api/campaigns \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Campaign","system":"DND5E"}'

curl http://localhost:3000/api/campaigns/<id>/role-mode

curl -X PUT http://localhost:3000/api/campaigns/<id>/role-mode \
  -H "Content-Type: application/json" \
  -d '{"roleMode":"GM"}'

curl http://localhost:3000/api/campaigns/<id>/items

curl -X POST http://localhost:3000/api/campaigns/<id>/items \
  -H "Content-Type: application/json" \
  -d '{"name":"Longsword","type":"WEAPON","description":"Steel blade"}'

curl -X POST http://localhost:3000/api/dev/reset

curl http://localhost:3000/api/preferences

curl -X PUT http://localhost:3000/api/preferences \
  -H "Content-Type: application/json" \
  -d '{"selectedCampaignId":"<id>"}'
```
