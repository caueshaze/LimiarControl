# FastAPI Server

## Requirements
- Python 3.11+
- Docker (for Postgres and Centrifugo)

## Run Postgres
```bash
docker compose up -d db centrifugo
```

This starts PostgreSQL on port `5432` and Centrifugo on port `8001`.

## Install deps
```bash
cd server_py
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

Use localhost-based values in `server_py/.env`:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/limiarcontrol
CORS_ORIGIN=http://localhost:5173,http://127.0.0.1:5173
AUTO_MIGRATE=true
JWT_SECRET=dev-secret-change-me
CENTRIFUGO_API_URL=http://localhost:8001/api
CENTRIFUGO_PUBLIC_URL=ws://localhost:8001/connection/websocket
CENTRIFUGO_TOKEN_SECRET=dev-secret-change-me
CENTRIFUGO_API_KEY=dev-api-key
```

If `server_py/.env` is reserved for production, keep your local database and
Centrifugo config in `server_py/.env.development.local`. The backend now
prefers that file automatically in development, so local runs stay on the dev
services by default:

```bash
cd server_py
uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload
```

## Run migrations
```bash
cd server_py
alembic upgrade head
```

In development, the API now runs `alembic upgrade head` automatically on startup by default.
Set `AUTO_MIGRATE=false` if you prefer fail-fast behavior instead of automatic upgrades.

## Seed base catalogs

After the schema is up to date, bootstrap the base item catalog from the repository JSON seed.

Import:

```bash
server_py/.venv/bin/python scripts/import_base_items_json.py --input Base/base_items.seed.json --replace
```

Export:

```bash
server_py/.venv/bin/python scripts/export_base_items_json.py --output Base/base_items.seed.json
```

Notes:

- `Base/base_items.seed.json` is the official bootstrap/backup file for base items
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
APP_ENV_FILE=.env.development.local uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload
```

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
