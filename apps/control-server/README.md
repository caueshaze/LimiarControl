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
cd apps/control-server
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
PORT=8000
CORS_ORIGIN=http://localhost:5173,http://127.0.0.1:5173
CENTRIFUGO_ALLOWED_ORIGINS=http://localhost:5173 http://127.0.0.1:5173 http://localhost:5174 http://127.0.0.1:5174 http://localhost:8000 http://127.0.0.1:8000
APP_ENV=development
AUTO_MIGRATE=true
JWT_SECRET=dev-secret-change-me
CENTRIFUGO_API_URL=http://localhost:8001/api
CENTRIFUGO_API_KEY=dev-api-key
CENTRIFUGO_PUBLIC_URL=ws://localhost:8001/connection/websocket
CENTRIFUGO_INTERNAL_WS_URL=ws://localhost:8001/connection/websocket
CENTRIFUGO_TOKEN_SECRET=dev-secret-change-me
CENTRIFUGO_TOKEN_HMAC_SECRET_KEY=dev-secret-change-me
LIMIAR_MAP_INTERNAL_KEY=dev-map-internal-key
```

When the API itself runs inside Docker, use `CENTRIFUGO_INTERNAL_WS_URL=ws://centrifugo:8000/connection/websocket`
so backend-to-backend realtime sync does not try to connect back to `localhost`.

## Run migrations
```bash
cd apps/control-server
alembic upgrade head
```

In development, the API now runs `alembic upgrade head` automatically on startup by default.
Set `AUTO_MIGRATE=false` if you prefer fail-fast behavior instead of automatic upgrades.

## Seed base catalogs

After the schema is up to date, bootstrap the base catalogs from the repository JSON seeds.

Items import:

```bash
apps/control-server/.venv/bin/python scripts/import_base_items_json.py --input Base/base_items.seed.json --replace
```

Items export:

```bash
apps/control-server/.venv/bin/python scripts/export_base_items_json.py --output Base/base_items.seed.json
```

Spells import:

```bash
apps/control-server/.venv/bin/python scripts/import_base_spells_json.py --input Base/base_spells.seed.json --replace
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

## Run the API (port 8000)
```bash
cd apps/control-server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Run lab locally

Use the lab env example from the repo root:

```bash
cp .env.lab.example .env.lab
docker compose --env-file .env.lab -f docker-compose.lab.yml up -d --build
```

Endpoints:

- App + API: `http://127.0.0.1:8002`
- API health: `http://127.0.0.1:8002/health`
- Centrifugo: `ws://127.0.0.1:8003/connection/websocket`

For browser access in homologation, prefer a reverse-proxied public URL such as
`wss://lab-limiar.example.com/centrifugo/connection/websocket` and keep
`LAB_CORS_ORIGIN` plus `LAB_CENTRIFUGO_ALLOWED_ORIGINS` aligned with that origin.

## Combat docs

- Phase 3A spell-combat notes: [docs/combat_spells_phase_3a.md](./docs/combat_spells_phase_3a.md)

## Curl examples
```bash
curl http://localhost:8000/api/campaigns

curl -X POST http://localhost:8000/api/campaigns \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Campaign","system":"DND5E"}'

curl http://localhost:8000/api/campaigns/<id>/role-mode

curl -X PUT http://localhost:8000/api/campaigns/<id>/role-mode \
  -H "Content-Type: application/json" \
  -d '{"roleMode":"GM"}'

curl http://localhost:8000/api/campaigns/<id>/items

curl -X POST http://localhost:8000/api/campaigns/<id>/items \
  -H "Content-Type: application/json" \
  -d '{"name":"Longsword","type":"WEAPON","description":"Steel blade"}'

curl -X POST http://localhost:8000/api/dev/reset

curl http://localhost:8000/api/preferences

curl -X PUT http://localhost:8000/api/preferences \
  -H "Content-Type: application/json" \
  -d '{"selectedCampaignId":"<id>"}'
```
